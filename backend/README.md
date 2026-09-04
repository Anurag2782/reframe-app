# Reframe — Backend

FastAPI service that does the actual image/video reframing: smart crop
(face + saliency detection), blurred-background padding, and an optional
AI-lite background extension mode (subject segmentation + composite).

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
# requires ffmpeg + ffprobe on your PATH, e.g.:
#   macOS:   brew install ffmpeg
#   Ubuntu:  sudo apt install ffmpeg
#   Windows: https://ffmpeg.org/download.html

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/batch-upload` | Upload 1+ files, kick off reframe jobs |
| GET | `/api/batch/{batch_id}` | Poll status of every job in a batch |
| GET | `/api/jobs/{job_id}` | Poll a single job |
| GET | `/api/download/{job_id}` | Download the finished file |
| GET | `/api/health` | Health check |

`batch-upload` form fields:
- `files`: one or more files (images or videos)
- `aspect`: one of `9:16`, `16:9`, `1:1`, `4:5` (or omit and pass `target_w`/`target_h` directly)
- `mode`: `crop` (smart crop), `pad` (blurred fill), or `ai_extend` (subject-segmentation composite, images only — falls back to `pad` for video)

## How the reframing works

- **`crop`** — runs face detection first (OpenCV Haar cascade), falls back to
  saliency detection to guess the main subject, then crops the largest
  possible window of the target aspect ratio centered on that subject. For
  video, it samples several frames across the clip and averages the subject
  position into one stable crop window, rather than re-cropping every frame
  (which would look jittery). See `app/video_processing.py` for the
  scene-by-scene upgrade path described in the project README.
- **`pad`** — keeps 100% of the original frame, scales it to fit inside the
  target dimensions, and fills the leftover space with a blurred, scaled-up
  copy of the same image/video (no black bars).
- **`ai_extend`** — uses `rembg` to cut the subject out, then composites it
  over a blurred/extended background. This is a lightweight stand-in for
  full generative outpainting; swapping in LaMa or Stable Diffusion
  Inpainting is a drop-in replacement inside `image_processing.py` if you
  want higher-quality (but slower, GPU-hungry) results.

## Storage & jobs

- Uploaded/processed files live in `storage/uploads` and `storage/outputs`
  (gitignored). Swap these for S3/R2 in production.
- Job state is tracked in a local SQLite file (`storage/jobs.db`) via
  `app/jobs.py`. Processing runs via FastAPI `BackgroundTasks`, so this
  works with zero extra infrastructure. For heavier production load, swap
  `BackgroundTasks` for Celery/RQ + Redis — the job-tracking functions in
  `app/jobs.py` are the seam to do that behind.
