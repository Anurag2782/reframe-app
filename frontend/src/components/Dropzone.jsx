import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

const ACCEPTED = {
  "image/jpeg": [],
  "image/png": [],
  "image/webp": [],
  "video/mp4": [],
  "video/quicktime": [],
  "video/webm": [],
};

export default function Dropzone({ onFilesSelected }) {
  const [pending, setPending] = useState([]);

  const onDrop = useCallback(
    (accepted) => {
      setPending((prev) => {
        const next = [...prev, ...accepted];
        onFilesSelected(next);
        return next;
      });
    },
    [onFilesSelected]
  );

  const removeFile = (idx) => {
    setPending((prev) => {
      const next = prev.filter((_, i) => i !== idx);
      onFilesSelected(next);
      return next;
    });
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: true,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`group relative rounded-2xl border-2 border-dashed p-12 text-center cursor-pointer transition-colors
          ${isDragActive ? "border-signal bg-signal/5" : "border-ink-600 hover:border-mist-500"}`}
      >
        <input {...getInputProps()} />
        <p className="font-display text-xl text-mist-100">
          {isDragActive ? "Drop it." : "Drag files here, or click to browse"}
        </p>
        <p className="mt-2 text-sm text-mist-500 font-mono">
          JPG · PNG · WEBP · MP4 · MOV · WEBM — up to 200MB each
        </p>
      </div>

      {pending.length > 0 && (
        <ul className="mt-4 divide-y divide-ink-700 rounded-xl border border-ink-700 overflow-hidden">
          {pending.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center justify-between px-4 py-2.5 bg-ink-800">
              <span className="text-sm text-mist-300 truncate font-mono">{f.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(i);
                }}
                className="text-mist-500 hover:text-bad text-sm ml-4 shrink-0"
                aria-label={`Remove ${f.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
