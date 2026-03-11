import { useCallback, useRef, useState } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"];

interface FileUploadProps {
  onUpload: (file: File) => void;
  disabled?: boolean;
  stagedFile?: File | null;
}

export default function FileUpload({ onUpload, disabled, stagedFile }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        alert("Unsupported file type. Please upload a JPEG, PNG, WEBP, or PDF file.");
        return;
      }
      onUpload(file);
    },
    [onUpload],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setDragOver(false), []);

  const onChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = "";
    },
    [handleFile],
  );

  const isStaged = !!stagedFile && !disabled;

  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={isStaged ? undefined : () => inputRef.current?.click()}
      className={`rounded-lg border-2 p-10 text-center transition-colors ${
        disabled
          ? "pointer-events-none border-gray-200 bg-gray-50 text-gray-400"
          : isStaged
            ? "border-gray-300 bg-white"
            : dragOver
              ? "cursor-pointer border-blue-500 bg-blue-50 text-blue-700"
              : "cursor-pointer border-dashed border-gray-300 bg-white text-gray-500 hover:border-gray-400"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,.pdf"
        onChange={onChange}
        className="hidden"
      />
      {isStaged ? (
        <>
          <p className="text-lg font-medium text-gray-700">{stagedFile.name}</p>
          <div className="mt-3 flex items-center justify-center gap-3">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onUpload(stagedFile);
              }}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Run Audit
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                inputRef.current?.click();
              }}
              className="text-sm text-gray-500 underline hover:text-gray-700"
            >
              Change file
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="text-lg font-medium">
            {disabled ? "Uploading..." : "Drop an invoice here"}
          </p>
          <p className="mt-1 text-sm">
            {disabled
              ? "Please wait while the audit is being processed"
              : "or click to browse — JPEG, PNG, WEBP, PDF"}
          </p>
        </>
      )}
    </div>
  );
}
