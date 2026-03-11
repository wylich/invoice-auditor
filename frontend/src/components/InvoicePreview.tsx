import { useEffect, useState } from "react";

interface InvoicePreviewProps {
  file: File;
}

export default function InvoicePreview({ file }: InvoicePreviewProps) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  if (!objectUrl) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <p className="mb-3 text-sm font-semibold text-gray-700">Invoice Preview</p>
      {file.type === "application/pdf" ? (
        <embed
          src={objectUrl}
          type="application/pdf"
          className="h-[600px] w-full rounded-lg border border-gray-200"
        />
      ) : (
        <img
          src={objectUrl}
          alt="Uploaded invoice"
          className="max-w-full rounded-lg border border-gray-200"
        />
      )}
    </div>
  );
}
