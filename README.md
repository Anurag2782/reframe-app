# Reframe

A free, open-source tool for converting images and videos between portrait
and landscape (and square, 4:5, etc.) — with smart cropping around the main
subject and blurred-background fill instead of black bars.

```
reframe-app/
  backend/     FastAPI service — the actual image/video processing (FFmpeg, OpenCV, Pillow)
  frontend/    React + Vite + Tailwind — drag-and-drop UI, batch queue, download
```

## Quick start (local dev)

You'll need Python 3.10+, Node 18+, and **FFmpeg** installed and on your PATH.

**1. Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Leave this running. API docs at `http://localhost:8000/docs`.

**2. Frontend** (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). Drag in a photo
or short video, pick a target aspect ratio and reframe mode, hit Convert.

That's the whole loop — upload happens over `POST /api/batch-upload`, the
frontend polls `GET /api/batch/{id}` every 1.5s until every file is `done`,
then each row gets a download link.

## What's implemented in this v1

- ✅ Rotate/resize/crop/pad for images (JPG, PNG, WEBP) and video (MP4, MOV, WEBM)
- ✅ Smart cropping: face detection first, saliency detection as a fallback, so the crop follows the actual subject instead of just cutting the center
- ✅ Blurred-background fill mode — zero content loss, no black bars
- ✅ "AI-lite" background extension mode for images (subject segmentation + composite) via `rembg`, with a designed extension point to swap in real generative outpainting (LaMa / Stable Diffusion inpainting) later
- ✅ Batch upload, background job processing, live status polling
- ✅ Drag-and-drop UI with aspect-ratio presets (9:16, 16:9, 1:1, 4:5)

I ran the full pipeline end-to-end during development (real image + real
video through `/api/batch-upload` → processing → `/api/download`) to confirm
it actually works, not just that it compiles.

## Known v1 simplifications, and how to grow past them

These are deliberate MVP shortcuts — noted so you know where to invest next:

1. **Video crop is one stable window, not scene-aware.** It samples ~6 frames
   across the clip and averages the subject position into a single crop
   window for the whole video. This avoids jitter but means a video with a
   scene cut (subject moves from left to right, or the shot changes
   entirely) won't re-center. Upgrade path: add `PySceneDetect`, compute a
   separate crop window per scene, and cross-fade or hard-cut between them
   in the FFmpeg filter graph.
2. **Job queue is FastAPI `BackgroundTasks` + SQLite**, not Celery/Redis.
   This is genuinely fine for a single-server deployment or personal use,
   but it means jobs don't survive a server crash mid-processing, and
   there's no retry/priority logic. Upgrade path: swap the calls in
   `app/jobs.py` for Celery tasks backed by Redis — the function signatures
   are already the seam for that.
3. **`ai_extend` mode is segmentation + blur composite, not true generative
   outpainting.** It's fast and free-tier-friendly, but it won't invent new
   background detail the way Stable Diffusion inpainting would. Swapping in
   a real inpainting model is a contained change inside
   `image_processing.py` (`ai_background_extend_image`) — treat it as a
   separate, optional, queued job since it's much slower and ideally wants
   a GPU.
4. **Storage is local disk.** Fine for dev; for production, point
   `UPLOAD_DIR`/`OUTPUT_DIR` at an S3-compatible bucket (Cloudflare R2 has a
   generous free tier) so the app can run on ephemeral hosting.
5. **No auth/rate limiting yet.** Fine for personal/local use; add both
   before exposing this publicly, especially given video processing is CPU-
   and disk-heavy.

## Deploying for free

- **Frontend**: `npm run build` in `frontend/`, deploy the `dist/` folder to
  Vercel, Netlify, or Cloudflare Pages (all free for static sites). Set
  `VITE_API_BASE` to your backend's public URL before building.
- **Backend**: Render, Railway, or Fly.io free tiers work for the API layer.
  Long video jobs may hit free-tier CPU/time limits — see the hosting
  section of the original project plan for the CPU-worker-on-a-free-VM
  pattern (e.g. Oracle Cloud's Always Free tier) if you outgrow this.

## License

Use whatever license you like for your own project — everything referenced
here (FFmpeg, OpenCV, Pillow, FastAPI, React, rembg) is free and
open-source, so there's nothing to license in from this stack itself.
