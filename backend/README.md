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
- `mode`: `ai_extend` (recommended), `ai_generate`, `pad`, or `crop`

## How the reframing works

- **`crop`** — runs face detection first (OpenCV Haar cascade), falls back to
  saliency detection to guess the main subject, then crops the largest
  possible window of the target aspect ratio centered on that subject. For
  video, it samples several frames across the clip and averages the subject
  position into one stable crop window, rather than re-cropping every frame
  (which would look jittery). See `app/video_processing.py` for the
  scene-by-scene upgrade path described in the project README.
  **This mode discards content by design** — whatever falls outside the
  crop window is gone.
- **`pad`** — keeps 100% of the original frame, scales it to fit inside the
  target dimensions, and fills the leftover space with a blurred, scaled-up
  copy of the same image/video (no black bars, but the fill area is
  visibly blurred).
- **`ai_extend`** — no blur, no cropping. For images: segments the subject
  out with `rembg`, uses OpenCV inpainting to erase it from the original so
  there's a clean background plate, extends that plate to the target size
  by mirroring its edges outward, then composites the original
  full-resolution subject back on top. The subject stays perfectly sharp;
  the extended area is a real (mirrored) continuation of the background,
  not a blur. For video, per-frame segmentation is too slow without a GPU
  worker, so this mode extends each frame's background by mirroring only
  (still no blur, just not subject-segmented).
  Note: `rembg`'s newer default model (Bria RMBG) carries a **non-commercial
  license** — the code explicitly pins `new_session("u2net")` instead, which
  is openly licensed and also much lighter (176MB vs 1GB).
- **`ai_generate`** — true generative outpainting: instead of mirroring
  existing pixels, a Stable Diffusion inpainting model paints in genuinely
  new background content for the extended area. Images only (video falls
  back to the same mirror extension as `ai_extend`, since per-frame
  diffusion isn't practical on CPU).

  **This does not run on your laptop by default in any meaningful way** —
  see `gpu-service/README.md` for running the actual model on a free/cheap
  GPU elsewhere (Google Colab, Hugging Face Spaces, or a cheap on-demand
  rental) and pointing this backend at it via the `GENERATIVE_REMOTE_URL`
  environment variable (see `.env.example`). Without that variable set, it
  falls back to running locally if `requirements-generative.txt` is
  installed (slow without a real GPU), and finally to mirror extension if
  neither is available — so the app never breaks, it just gets
  progressively simpler.

## Storage & jobs

- Uploaded/processed files live in `storage/uploads` and `storage/outputs`
  (gitignored). Swap these for S3/R2 in production.
- Job state is tracked in a local SQLite file (`storage/jobs.db`) via
  `app/jobs.py`. Processing runs via FastAPI `BackgroundTasks`, so this
  works with zero extra infrastructure. For heavier production load, swap
  `BackgroundTasks` for Celery/RQ + Redis — the job-tracking functions in
  `app/jobs.py` are the seam to do that behind.