# Reframe — Frontend

React + Vite + Tailwind UI: drag-and-drop upload, aspect ratio / reframe-mode
picker, live batch progress, download links.

## Run it

```bash
npm install
npm run dev
```

Talks to the backend at `http://localhost:8000` by default. To point at a
different backend (e.g. a deployed one), copy `.env.example` to `.env` and
set `VITE_API_BASE`.

## Build for production

```bash
npm run build
```

Outputs static files to `dist/` — deploy that folder to Vercel, Netlify,
Cloudflare Pages, or any static host.
