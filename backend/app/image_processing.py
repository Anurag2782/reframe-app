"""
Core image reframing logic: smart crop (face + saliency based) and
blurred-background padding, used for both standalone images and as the
per-frame/per-scene logic for video.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageFilter

_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


@dataclass
class CropWindow:
    x: int
    y: int
    w: int
    h: int


def find_subject_center(cv_image: np.ndarray) -> tuple[int, int]:
    """Return (cx, cy) of the most likely subject: faces first, else saliency,
    else image center."""
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

    if len(faces) > 0:
        xs = [x + w / 2 for (x, y, w, h) in faces]
        ys = [y + h / 2 for (x, y, w, h) in faces]
        return int(np.mean(xs)), int(np.mean(ys))

    try:
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        success, sal_map = saliency.computeSaliency(cv_image)
        if success:
            sal_map = (sal_map * 255).astype("uint8")
            _, thresh = cv2.threshold(sal_map, 200, 255, cv2.THRESH_BINARY)
            m = cv2.moments(thresh)
            if m["m00"] != 0:
                return int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])
    except Exception:
        pass

    h, w = cv_image.shape[:2]
    return w // 2, h // 2


def compute_crop_window(src_w: int, src_h: int, target_w: int, target_h: int,
                         subject_cx: int, subject_cy: int) -> CropWindow:
    """Compute the largest crop window matching target aspect ratio, centered
    on the subject but clamped to image bounds."""
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        crop_h = src_h
        crop_w = int(round(src_h * target_ratio))
    else:
        crop_w = src_w
        crop_h = int(round(src_w / target_ratio))

    x = max(0, min(subject_cx - crop_w // 2, src_w - crop_w))
    y = max(0, min(subject_cy - crop_h // 2, src_h - crop_h))
    return CropWindow(x=x, y=y, w=crop_w, h=crop_h)


def smart_crop_image(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    cv_img = cv2.imread(input_path)
    if cv_img is None:
        raise ValueError(f"Could not read image: {input_path}")
    src_h, src_w = cv_img.shape[:2]

    cx, cy = find_subject_center(cv_img)
    win = compute_crop_window(src_w, src_h, target_w, target_h, cx, cy)

    cropped = cv_img[win.y:win.y + win.h, win.x:win.x + win.w]
    resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(output_path, resized)


def pad_with_blur_image(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    """Fit the whole image inside the target frame, filling the border with a
    blurred, scaled-up copy of the same image (no content is lost)."""
    img = Image.open(input_path).convert("RGB")
    src_w, src_h = img.size

    scale = min(target_w / src_w, target_h / src_h)
    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    resized = img.resize(new_size, Image.LANCZOS)

    bg = img.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
    paste_pos = ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2)
    bg.paste(resized, paste_pos)
    bg.save(output_path, quality=95)


def ai_background_extend_image(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    """'AI-lite' background extension: segment the subject out with rembg,
    then composite it over a blurred/extended version of the original.
    Falls back to pad_with_blur_image if rembg isn't installed/available.
    """
    try:
        from rembg import remove
    except ImportError:
        pad_with_blur_image(input_path, output_path, target_w, target_h)
        return

    with open(input_path, "rb") as f:
        input_bytes = f.read()

    subject_bytes = remove(input_bytes)
    subject = Image.open(io.BytesIO(subject_bytes)).convert("RGBA")

    original = Image.open(input_path).convert("RGB")
    bg = original.resize((target_w, target_h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(35)).convert("RGBA")

    scale = min(target_w / subject.width, target_h / subject.height)
    new_size = (max(1, int(subject.width * scale)), max(1, int(subject.height * scale)))
    subject_resized = subject.resize(new_size, Image.LANCZOS)

    paste_pos = ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2)
    bg.paste(subject_resized, paste_pos, subject_resized)
    bg.convert("RGB").save(output_path, quality=95)


def reframe_image(input_path: str, output_path: str, target_w: int, target_h: int, mode: str) -> None:
    """mode: 'crop' | 'pad' | 'ai_extend'"""
    if mode == "crop":
        smart_crop_image(input_path, output_path, target_w, target_h)
    elif mode == "pad":
        pad_with_blur_image(input_path, output_path, target_w, target_h)
    elif mode == "ai_extend":
        ai_background_extend_image(input_path, output_path, target_w, target_h)
    else:
        raise ValueError(f"Unknown mode: {mode}")
