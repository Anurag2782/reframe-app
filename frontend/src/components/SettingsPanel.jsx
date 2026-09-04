const ASPECTS = [
  { id: "9:16", label: "9:16", hint: "Reels · Shorts · Stories", w: 1, h: 1.78 },
  { id: "16:9", label: "16:9", hint: "YouTube · widescreen", w: 1.78, h: 1 },
  { id: "1:1", label: "1:1", hint: "Feed square", w: 1, h: 1 },
  { id: "4:5", label: "4:5", hint: "Feed portrait", w: 1, h: 1.25 },
];

const MODES = [
  {
    id: "ai_extend",
    label: "AI extend (recommended)",
    desc: "Cuts the subject out, keeps it perfectly sharp, and extends the background by mirroring it outward — no blur. Images: fully subject-aware. Video: background-only extension (per-frame segmentation isn't fast enough yet).",
  },
  {
    id: "ai_generate",
    label: "AI generate",
    desc: "Uses a generative AI model to paint in genuinely new background detail for the extended area, instead of mirroring or blurring. Images only, much slower, needs optional extra dependencies installed on the backend.",
  },
  {
    id: "pad",
    label: "Blur fill",
    desc: "Keeps 100% of the original frame — nothing is cropped. Fills empty space with a blurred, stretched extension. Fast, always available, no extra setup.",
  },
  {
    id: "crop",
    label: "Smart crop",
    desc: "Crops the edges down to the target shape, centered on the detected subject. Faster to watch, but permanently discards whatever falls outside the crop.",
  },
];

function AspectGlyph({ w, h, active }) {
  const maxDim = 22;
  const scale = maxDim / Math.max(w, h);
  const rw = w * scale;
  const rh = h * scale;
  return (
    <svg width={26} height={26} viewBox="0 0 26 26" className="shrink-0">
      <rect
        x={(26 - rw) / 2}
        y={(26 - rh) / 2}
        width={rw}
        height={rh}
        rx={2}
        fill="none"
        stroke={active ? "#ffb238" : "#8b93a1"}
        strokeWidth={2}
      />
    </svg>
  );
}

export default function SettingsPanel({ aspect, setAspect, mode, setMode }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-display text-sm uppercase tracking-wide text-mist-500 mb-3">
          Target format
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {ASPECTS.map((a) => (
            <button
              key={a.id}
              onClick={() => setAspect(a.id)}
              className={`flex items-center gap-3 rounded-xl border px-3 py-3 text-left transition-colors
                ${
                  aspect === a.id
                    ? "border-signal bg-signal/10"
                    : "border-ink-700 bg-ink-800 hover:border-ink-600"
                }`}
            >
              <AspectGlyph w={a.w} h={a.h} active={aspect === a.id} />
              <span>
                <span className="block font-mono text-sm text-mist-100">{a.label}</span>
                <span className="block text-xs text-mist-500">{a.hint}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 className="font-display text-sm uppercase tracking-wide text-mist-500 mb-3">
          Reframe method
        </h3>
        <div className="space-y-2">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`w-full rounded-xl border px-4 py-3 text-left transition-colors
                ${
                  mode === m.id
                    ? "border-signal bg-signal/10"
                    : "border-ink-700 bg-ink-800 hover:border-ink-600"
                }`}
            >
              <span className="block font-display text-sm text-mist-100">{m.label}</span>
              <span className="block text-xs text-mist-500 mt-0.5">{m.desc}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}