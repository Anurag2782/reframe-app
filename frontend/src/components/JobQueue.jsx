import { useEffect, useRef, useState } from "react";
import { getBatchStatus } from "../lib/api";
import JobRow from "./JobRow";

export default function JobQueue({ batchId }) {
  const [jobs, setJobs] = useState([]);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!batchId) return;

    const poll = async () => {
      try {
        const data = await getBatchStatus(batchId);
        setJobs(data.jobs);
        const stillWorking = data.jobs.some((j) => j.status === "queued" || j.status === "processing");
        if (!stillWorking && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch (e) {
        console.error(e);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 1500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
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