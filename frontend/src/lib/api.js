const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function uploadBatch(files, { aspect, mode, targetW, targetH }) {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  if (aspect) formData.append("aspect", aspect);
  if (mode) formData.append("mode", mode);
  if (targetW) formData.append("target_w", targetW);
  if (targetH) formData.append("target_h", targetH);

  const res = await fetch(`${API_BASE}/api/batch-upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function getBatchStatus(batchId) {
  const res = await fetch(`${API_BASE}/api/batch/${batchId}`);
  if (!res.ok) throw new Error(`Failed to fetch batch status (${res.status})`);
  return res.json();
}

export function downloadUrl(jobId) {
  return `${API_BASE}/api/download/${jobId}`;
}

/**
 * Downloads a job's result via fetch + blob instead of a plain <a href>.
 * Files are single-use on the server (deleted immediately after the first
 * successful download), so a stale link needs to surface as a real error
 * message -- a plain <a> tag would otherwise silently "download" the
 * server's JSON error body as a corrupt file.
 */
export async function downloadJobResult(jobId, filename) {
  const res = await fetch(downloadUrl(jobId));
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename || "reframed-file";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}