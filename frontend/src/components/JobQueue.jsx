import { useEffect, useRef, useState } from "react";
import { getBatchStatus, downloadUrl } from "../lib/api";
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

  const doneJobs = jobs.filter((j) => j.status === "done");
  const allDone = jobs.length > 0 && doneJobs.length === jobs.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display text-sm uppercase tracking-wide text-mist-500">
          Batch — {jobs.length} file{jobs.length !== 1 ? "s" : ""}
        </h3>
        {allDone && jobs.length > 1 && (
          <div className="flex gap-1 flex-wrap justify-end">
            {doneJobs.map((j) => (
              <a
                key={j.id}
                href={downloadUrl(j.id)}
                className="text-xs font-mono px-2 py-1 rounded bg-ink-700 text-mist-300 hover:text-signal"
              >
                {j.filename}
              </a>
            ))}
          </div>
        )}
      </div>
      <ul className="divide-y divide-ink-700 rounded-xl border border-ink-700 overflow-hidden">
        {jobs.map((job) => (
          <JobRow key={job.id} job={job} />
        ))}
      </ul>
    </div>
  );
}
