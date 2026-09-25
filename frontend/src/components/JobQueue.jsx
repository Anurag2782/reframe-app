import { useEffect, useRef, useState } from "react";
import { getBatchStatus } from "../lib/api";
import JobRow from "./JobRow";

const INITIAL_POLL_MS = 2000;
const MAX_POLL_MS = 30000;

export default function JobQueue({ batchId }) {
  const [jobs, setJobs] = useState([]);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (!batchId) return;

    let stopped = false;
    let pollDelay = INITIAL_POLL_MS;

    const schedulePoll = (delay) => {
      timeoutRef.current = setTimeout(poll, delay);
    };

    const poll = async () => {
      if (stopped) return;
      try {
        const data = await getBatchStatus(batchId);
        if (stopped) return;
        setJobs(data.jobs);
        const stillWorking = data.jobs.some((j) => j.status === "queued" || j.status === "processing");
        pollDelay = INITIAL_POLL_MS;
        if (stillWorking) {
          schedulePoll(pollDelay);
        }
      } catch (e) {
        if (stopped) return;
        // Back off on Render throttling or a transient instance restart.
        const serverRetry = e.retryAfterMs || 0;
        pollDelay = Math.min(Math.max(pollDelay * 2, 5000), MAX_POLL_MS);
        schedulePoll(Math.max(serverRetry, pollDelay));
      }
    };

    poll();
    return () => {
      stopped = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [batchId]);

  if (!batchId) return null;

  return (
    <div>
      <h3 className="font-display text-sm uppercase tracking-wide text-mist-500 mb-3">
        Batch — {jobs.length} file{jobs.length !== 1 ? "s" : ""}
      </h3>
      <ul className="divide-y divide-ink-700 rounded-xl border border-ink-700 overflow-hidden">
        {jobs.map((job) => (
          <JobRow key={job.id} job={job} />
        ))}
      </ul>
      <p className="mt-2 text-xs text-mist-500 font-mono">
        Files are removed from the server right after you download them — grab each one once.
      </p>
    </div>
  );
}