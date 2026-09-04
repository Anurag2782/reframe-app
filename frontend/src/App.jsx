import { useState } from "react";
import ViewfinderMark from "./components/ViewfinderMark";
import Dropzone from "./components/Dropzone";
import SettingsPanel from "./components/SettingsPanel";
import JobQueue from "./components/JobQueue";
import { uploadBatch } from "./lib/api";

export default function App() {
  const [files, setFiles] = useState([]);
  const [aspect, setAspect] = useState("9:16");
  const [mode, setMode] = useState("pad"); // "pad" keeps 100% of the frame; "crop" is opt-in
  const [batchId, setBatchId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleConvert = async () => {
    if (files.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await uploadBatch(files, { aspect, mode });
      setBatchId(res.batch_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800">
        <div className="max-w-5xl mx-auto px-6 py-5 flex items-center gap-3">
          <ViewfinderMark size={36} />
          <div>
            <h1 className="font-display text-lg text-mist-100 leading-tight">Reframe</h1>
            <p className="text-xs text-mist-500 font-mono leading-tight">
              portrait ⇄ landscape, without losing the shot
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 grid md:grid-cols-[1fr_320px] gap-8">
        <section className="space-y-6">
          <Dropzone onFilesSelected={setFiles} />

          {error && (
            <p className="text-sm text-bad font-mono border border-bad/30 bg-bad/5 rounded-lg px-4 py-2">
              {error}
            </p>
          )}

          <button
            onClick={handleConvert}
            disabled={files.length === 0 || submitting}
            className="w-full rounded-xl bg-signal text-ink-950 font-display font-semibold py-3 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white transition-colors"
          >
            {submitting
              ? "Uploading…"
              : `Convert ${files.length > 0 ? `${files.length} file${files.length > 1 ? "s" : ""}` : ""} to ${aspect}`}
          </button>

          {batchId && (
            <div className="pt-4">
              <JobQueue batchId={batchId} />
            </div>
          )}
        </section>

        <aside className="bg-ink-900/50 rounded-2xl border border-ink-800 p-5 h-fit">
          <SettingsPanel aspect={aspect} setAspect={setAspect} mode={mode} setMode={setMode} />
        </aside>
      </main>

      <footer className="max-w-5xl mx-auto px-6 pb-10">
        <p className="text-xs text-mist-500 font-mono">
          Built on FFmpeg, OpenCV & Pillow — free and open-source end to end.
        </p>
      </footer>
    </div>
  );
}