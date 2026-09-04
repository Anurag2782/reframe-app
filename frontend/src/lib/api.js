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
