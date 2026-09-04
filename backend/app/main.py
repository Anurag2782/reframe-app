from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import jobs
from .image_processing import reframe_image
from .video_processing import reframe_video

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
MAX_FILE_SIZE_MB = 200

ASPECT_PRESETS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}

app = FastAPI(title="Reframe API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your frontend's origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    jobs.init_db()


def _media_type_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


def _resolve_target_dims(aspect: str | None, target_w: int | None, target_h: int | None) -> tuple[int, int]:
    if target_w and target_h:
        return target_w, target_h
    if aspect and aspect in ASPECT_PRESETS:
        return ASPECT_PRESETS[aspect]
    raise HTTPException(status_code=400, detail="Provide either a known aspect preset or target_w/target_h")


def _process_job(job_id: str) -> None:
    job = jobs.get_job(job_id)
    if job is None:
        return
    jobs.update_job(job_id, status="processing")
    try:
        output_ext = ".jpg" if job["media_type"] == "image" else ".mp4"
        output_path = OUTPUT_DIR / f"{job_id}{output_ext}"

        if job["media_type"] == "image":
            reframe_image(job["input_path"], str(output_path), job["target_w"], job["target_h"], job["mode"])
        else:
            reframe_video(job["input_path"], str(output_path), job["target_w"], job["target_h"], job["mode"])

        jobs.update_job(job_id, status="done", output_path=str(output_path))
    except Exception as e:  # noqa: BLE001
        jobs.update_job(job_id, status="failed", error=str(e))


@app.post("/api/batch-upload")
async def batch_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    aspect: str | None = Form(default="9:16"),
    mode: str = Form(default="crop"),  # 'crop' | 'pad' | 'ai_extend'
    target_w: int | None = Form(default=None),
    target_h: int | None = Form(default=None),
):
    if mode not in ("crop", "pad", "ai_extend", "ai_generate"):
        raise HTTPException(status_code=400, detail="mode must be 'crop', 'pad', 'ai_extend', or 'ai_generate'")

    tw, th = _resolve_target_dims(aspect, target_w, target_h)
    batch_id = str(uuid.uuid4())
    job_ids = []

    for f in files:
        media_type = _media_type_for(f.filename)

        contents = await f.read()
        if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"{f.filename} exceeds {MAX_FILE_SIZE_MB}MB limit")

        ext = Path(f.filename).suffix.lower()
        stored_name = f"{uuid.uuid4()}{ext}"
        input_path = UPLOAD_DIR / stored_name
        with open(input_path, "wb") as out:
            out.write(contents)

        job_id = jobs.create_job(
            batch_id=batch_id,
            filename=f.filename,
            media_type=media_type,
            target_w=tw,
            target_h=th,
            mode=mode,
            input_path=str(input_path),
        )
        job_ids.append(job_id)
        background_tasks.add_task(_process_job, job_id)

    return {"batch_id": batch_id, "job_ids": job_ids}


@app.get("/api/batch/{batch_id}")
def get_batch_status(batch_id: str):
    job_list = jobs.list_jobs_for_batch(batch_id)
    if not job_list:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch_id, "jobs": job_list}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/download/{job_id}")
def download_result(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done" or not job["output_path"]:
        raise HTTPException(status_code=409, detail=f"Job is not ready (status: {job['status']})")

    path = job["output_path"]
    media_type, _ = mimetypes.guess_type(path)
    filename = f"reframed_{job['filename']}"
    return FileResponse(path, media_type=media_type or "application/octet-stream", filename=filename)


@app.get("/api/health")
def health():
    return {"status": "ok"}