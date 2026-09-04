"""
Video reframing via FFmpeg. Strategy:
  1. Probe video dimensions with ffprobe.
  2. For 'crop' mode: sample a handful of frames across the video, run the
     same subject-detection used for images on each, and average the
     resulting crop windows into a single stable window (avoids jitter).
     This is a v1 simplification -- see README for the scene-aware upgrade.
  3. For 'pad' mode: no analysis needed, just an FFmpeg filter graph.
  4. Encode with libx264/aac.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass

import cv2
import numpy as np

from .image_processing import find_subject_center, compute_crop_window, CropWindow


@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float


def probe_video(path: str) -> VideoInfo:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "json", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    return VideoInfo(width=int(stream["width"]), height=int(stream["height"]), duration=duration)


def _sample_frame_centers(path: str, info: VideoInfo, num_samples: int = 6) -> list[tuple[int, int]]:
    cap = cv2.VideoCapture(path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    centers = []

    for i in range(num_samples):
        frame_idx = int(total_frames * (i + 0.5) / num_samples)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        cx, cy = find_subject_center(frame)
        centers.append((cx, cy))

    cap.release()
    if not centers:
        centers = [(info.width // 2, info.height // 2)]
    return centers


def compute_stable_crop_window(path: str, info: VideoInfo, target_w: int, target_h: int) -> CropWindow:
    centers = _sample_frame_centers(path, info)
    avg_cx = int(np.mean([c[0] for c in centers]))
    avg_cy = int(np.mean([c[1] for c in centers]))
    return compute_crop_window(info.width, info.height, target_w, target_h, avg_cx, avg_cy)


def reframe_video_crop(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    info = probe_video(input_path)
    win = compute_stable_crop_window(input_path, info, target_w, target_h)

    vf = f"crop={win.w}:{win.h}:{win.x}:{win.y},scale={target_w}:{target_h}:flags=lanczos"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def reframe_video_pad(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    """Blurred-background fill, no cropping -- keeps 100% of the original frame.

    The foreground must be fit inside BOTH target_w and target_h (whichever is
    the tighter constraint), not just scaled by width. Scaling by width alone
    works fine when going landscape->portrait (there's vertical slack to
    absorb any overflow), but breaks badly on portrait->landscape: scaling a
    tall source to the full target width produces a foreground far taller
    than the target canvas, and ffmpeg's overlay filter silently clips
    anything outside the canvas -- which looks like an unexplained crop/zoom.
    force_original_aspect_ratio=decrease with BOTH dimensions given fixes
    this by shrinking to fit whichever axis is tighter, exactly like the
    equivalent Pillow logic in image_processing.pad_with_blur_image.
    """
    vf = (
        f"split[bg][fg];"
        f"[bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},boxblur=20:1,setsar=1[bgblur];"
        f"[fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1[fgscaled];"
        f"[bgblur][fgscaled]overlay=(W-w)/2:(H-h)/2"
    )
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def reframe_video(input_path: str, output_path: str, target_w: int, target_h: int, mode: str) -> None:
    if mode == "crop":
        reframe_video_crop(input_path, output_path, target_w, target_h)
    elif mode in ("pad", "ai_extend"):  # ai_extend not yet supported for video -> falls back to pad
        reframe_video_pad(input_path, output_path, target_w, target_h)
    else:
        raise ValueError(f"Unknown mode: {mode}")