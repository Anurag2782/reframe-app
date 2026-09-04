"""
Standalone generative-outpainting inference service.

This is deliberately a SEPARATE, minimal FastAPI app from the main backend.
It does the one heavy thing -- loading a Stable Diffusion inpainting model
onto a GPU and running it -- and nothing else. Run this wherever you have a
GPU (Colab, Kaggle, Hugging Face Spaces, RunPod, a cloud VM, ...), and point
your main backend at it with the GENERATIVE_REMOTE_URL environment variable.
Your laptop never loads the model or touches a GPU.

Endpoints:
  GET  /health              -> {"status": "ok", "device": "cuda" | "cpu"}
  POST /outpaint             -> multipart form:
                                   image: the seed canvas (PNG/JPEG)
                                   mask:  the inpainting mask (PNG, white = generate)
                                   prompt: optional text prompt
                                 returns: generated PNG image bytes
"""
from __future__ import annotations

import io
import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image

app = FastAPI(title="Reframe GPU Service")

_pipe = None
_device = None


def _get_pipeline():
    """Lazy-load the model on first request, not at import time, so
    /health responds instantly even before the (large) model is loaded."""
    global _pipe, _device
    if _pipe is not None:
        return _pipe

    import torch
    from diffusers import AutoPipelineForInpainting

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    model_id = os.environ.get("GENERATIVE_MODEL_ID", "stabilityai/stable-diffusion-2-inpainting")

    _pipe = AutoPipelineForInpainting.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
    ).to(_device)

    return _pipe


@app.get("/health")
def health():
    import torch
    return {
        "status": "ok",
        "cuda_available": torch.cuda.is_available(),
        "model_loaded": _pipe is not None,
    }


@app.post("/outpaint")
async def outpaint(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: str = Form(default="extend the background naturally, photorealistic, seamless, consistent lighting"),
    steps: int = Form(default=30),
):
    pipe = _get_pipeline()

    image_bytes = await image.read()
    mask_bytes = await mask.read()

    seed_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")

    result = pipe(
        prompt=prompt,
        image=seed_img,
        mask_image=mask_img,
        num_inference_steps=steps,
    ).images[0]

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")