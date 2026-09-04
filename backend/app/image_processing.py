"""
Core image reframing logic: smart crop (face + saliency based), blurred-
background padding, non-blurred AI-assisted background extension, and true
generative outpainting -- used for standalone images and as the
per-frame/per-scene logic for video.
"""
from __future__ import annotations

import io
import os
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


def mirror_extend_image(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    """Fit the image inside the target frame, then extend the canvas outward
    by mirroring the edge content -- no blur, no stretching. Good for
    continuous backgrounds (sky, grass, walls, fabric); can look repetitive
    on busy/detailed backgrounds, which is what 'ai_generate' mode is for.
    """
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Could not read image: {input_path}")
    src_h, src_w = img.shape[:2]

    scale = min(target_w / src_w, target_h / src_h)
    new_w, new_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    pad_w = target_w - new_w
    pad_h = target_h - new_h
    top, bottom = pad_h // 2, pad_h - pad_h // 2
    left, right = pad_w // 2, pad_w - pad_w // 2

    extended = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_REFLECT_101)
    cv2.imwrite(output_path, extended)


def ai_background_extend_image(input_path: str, output_path: str, target_w: int, target_h: int) -> None:
    """Extends the canvas to the target size with the subject perfectly
    sharp on top -- no blur anywhere. Strategy:
      1. Segment the subject out with rembg (alpha mask).
      2. Use OpenCV inpainting to erase the subject from the original photo,
         producing a plausible subject-free background plate.
      3. Extend that clean plate to the target size by mirroring its edges
         outward (mirror_extend_image) -- continuous, not blurred.
      4. Composite the original full-resolution subject back on top, at the
         same position/scale it occupied before extension.
    Falls back to mirror_extend_image (still no blur, just not subject-aware)
    if rembg isn't installed.
    """
    try:
        from rembg import remove, new_session
    except ImportError:
        mirror_extend_image(input_path, output_path, target_w, target_h)
        return

    # Pin to u2net explicitly: newer rembg versions default to Bria's RMBG
    # model, which carries a non-commercial license -- not appropriate for a
    # free/open-source tool. u2net is openly licensed and much lighter.
    session = new_session("u2net")

    with open(input_path, "rb") as f:
        input_bytes = f.read()
    subject_rgba = Image.open(io.BytesIO(remove(input_bytes, session=session))).convert("RGBA")

    original_cv = cv2.imread(input_path)
    if original_cv is None:
        raise ValueError(f"Could not read image: {input_path}")
    src_h, src_w = original_cv.shape[:2]

    alpha = np.array(subject_rgba.split()[-1])
    subject_mask = (alpha > 10).astype("uint8") * 255
    subject_mask = cv2.dilate(subject_mask, np.ones((9, 9), np.uint8))  # clean up soft edges too

    clean_plate = cv2.inpaint(original_cv, subject_mask, 7, cv2.INPAINT_TELEA)

    tmp_plate_path = output_path + ".plate.png"
    cv2.imwrite(tmp_plate_path, clean_plate)
    try:
        mirror_extend_image(tmp_plate_path, output_path, target_w, target_h)
    finally:
        os.remove(tmp_plate_path)

    canvas = Image.open(output_path).convert("RGBA")
    scale = min(target_w / src_w, target_h / src_h)
    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    subject_resized = subject_rgba.resize(new_size, Image.LANCZOS)
    paste_pos = ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2)
    canvas.paste(subject_resized, paste_pos, subject_resized)
    canvas.convert("RGB").save(output_path, quality=95)


def _build_outpaint_seed_and_mask(input_path: str, target_w: int, target_h: int, output_path: str):
    """Shared prep for generative outpainting: builds the mirror-seeded
    canvas (so the model has real pixels to blend from at the seam, not
    blank space) and the generation mask. Used by both the local and
    remote code paths so they stay in sync."""
    img = Image.open(input_path).convert("RGB")
    src_w, src_h = img.size
    scale = min(target_w / src_w, target_h / src_h)
    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    paste_pos = ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2)

    seed_path = output_path + ".seed.png"
    mirror_extend_image(input_path, seed_path, target_w, target_h)
    seed_canvas = Image.open(seed_path).convert("RGB")
    os.remove(seed_path)

    mask = Image.new("L", (target_w, target_h), 255)  # white = generate
    mask.paste(0, paste_pos + (paste_pos[0] + new_size[0], paste_pos[1] + new_size[1]))  # black = keep

    return seed_canvas, mask


def _generative_outpaint_remote(seed_canvas: "Image.Image", mask: "Image.Image", output_path: str,
                                 prompt: str, remote_url: str) -> bool:
    """POSTs the seed canvas + mask to a separately-hosted GPU service (see
    gpu-service/app.py and gpu-service/README.md) instead of loading the
    model in-process. Returns True on success, False if the remote call
    fails for any reason (caller should fall back)."""
    try:
        import requests
    except ImportError:
        return False

    seed_buf = io.BytesIO()
    seed_canvas.save(seed_buf, format="PNG")
    seed_buf.seek(0)

    mask_buf = io.BytesIO()
    mask.save(mask_buf, format="PNG")
    mask_buf.seek(0)

    try:
        resp = requests.post(
            f"{remote_url.rstrip('/')}/outpaint",
            files={
                "image": ("seed.png", seed_buf, "image/png"),
                "mask": ("mask.png", mask_buf, "image/png"),
            },
            data={"prompt": prompt},
            timeout=120,
        )
        resp.raise_for_status()
    except Exception:
        return False

    with open(output_path, "wb") as f:
        f.write(resp.content)
    return True


def generative_outpaint_image(input_path: str, output_path: str, target_w: int, target_h: int,
                               prompt: str = "extend the background naturally, "
                                             "photorealistic, seamless, consistent lighting") -> None:
    """True generative outpainting: the newly-created canvas area is filled
    with AI-generated content that matches the scene, rather than a
    mirrored or blurred copy of existing pixels.

    Resolution order:
      1. If GENERATIVE_REMOTE_URL is set, POST the job to that GPU service
         (see gpu-service/) instead of running the model here. This is the
         recommended setup for a laptop/CPU-only machine -- see
         gpu-service/README.md for hosting it on Colab, Hugging Face
         Spaces, or a cheap GPU rental, so your own machine's memory and
         GPU are never touched.
      2. Otherwise, if the optional heavy dependencies in
         requirements-generative.txt are installed locally, run the model
         in-process (needs a real GPU to be fast; slow on CPU).
      3. Otherwise, fall back to mirror_extend_image, so the app keeps
         working either way.
    """
    remote_url = os.environ.get("GENERATIVE_REMOTE_URL")
    if remote_url:
        seed_canvas, mask = _build_outpaint_seed_and_mask(input_path, target_w, target_h, output_path)
        if _generative_outpaint_remote(seed_canvas, mask, output_path, prompt, remote_url):
            return
        # Remote call failed (service asleep, network issue, etc.) -- fall
        # through to local/mirror rather than erroring the whole job out.

    try:
        import torch
        from diffusers import AutoPipelineForInpainting
    except ImportError:
        mirror_extend_image(input_path, output_path, target_w, target_h)
        return

    seed_canvas, mask = _build_outpaint_seed_and_mask(input_path, target_w, target_h, output_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = AutoPipelineForInpainting.from_pretrained(
        "stabilityai/stable-diffusion-2-inpainting",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    ).to(device)

    result = pipe(
        prompt=prompt,
        image=seed_canvas,
        mask_image=mask,
        num_inference_steps=30,
    ).images[0]

    result.save(output_path, quality=95)


def reframe_image(input_path: str, output_path: str, target_w: int, target_h: int, mode: str) -> None:
    """mode: 'crop' | 'pad' | 'ai_extend' | 'ai_generate'"""
    if mode == "crop":
        smart_crop_image(input_path, output_path, target_w, target_h)
    elif mode == "pad":
        pad_with_blur_image(input_path, output_path, target_w, target_h)
    elif mode == "ai_extend":
        ai_background_extend_image(input_path, output_path, target_w, target_h)
    elif mode == "ai_generate":
        generative_outpaint_image(input_path, output_path, target_w, target_h)
    else:
        raise ValueError(f"Unknown mode: {mode}")