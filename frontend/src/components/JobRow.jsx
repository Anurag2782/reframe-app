import { downloadUrl } from "../lib/api";

const STATUS_STYLES = {
  queued: { label: "Queued", color: "text-mist-500", dot: "bg-mist-500" },
  processing: { label: "Reframing…", color: "text-signal", dot: "bg-signal animate-pulse" },
  done: { label: "Done", color: "text-ok", dot: "bg-ok" },
  failed: { label: "Failed", color: "text-bad", dot: "bg-bad" },
};

export default function JobRow({ job }) {
  const status = STATUS_STYLES[job.status] || STATUS_STYLES.queued;

  return (
    <li className="flex items-center justify-between gap-4 px-4 py-3 bg-ink-800">
      <div className="min-w-0 flex items-center gap-3">
        <span className={`h-2 w-2 rounded-full shrink-0 ${status.dot}`} />
        <div className="min-w-0">
          <p className="text-sm text-mist-100 truncate font-mono">{job.filename}</p>
          <p className={`text-xs ${status.color}`}>
            {status.label}
            {job.status === "failed" && job.error ? ` — ${job.error}` : ""}
          </p>
        </div>
      </div>

      {job.status === "done" ? (
        <a
          href={downloadUrl(job.id)}
          className="shrink-0 text-xs font-mono px-3 py-1.5 rounded-lg bg-signal text-ink-950 hover:bg-signal-dim transition-colors"
        >
          Download
        </a>
      ) : (
        <span className="shrink-0 text-xs font-mono text-mist-500 px-3 py-1.5">
          {job.target_w}×{job.target_h}
        </span>
      )}
    </li>
  );
}
