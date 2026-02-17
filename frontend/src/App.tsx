import { useCallback, useState } from "react";
import Header from "./components/Header";
import PrivacyNotice from "./components/PrivacyNotice";
import FileUpload from "./components/FileUpload";
import AuditResult from "./components/AuditResult";
import { createAudit } from "./api";
import type { Invoice } from "./types";

export default function App() {
  const [uploading, setUploading] = useState(false);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    setInvoice(null);

    try {
      const result = await createAudit(file);
      setInvoice(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setUploading(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="mx-auto max-w-4xl space-y-6 px-4 py-8">
        <PrivacyNotice />
        <FileUpload onUpload={handleUpload} disabled={uploading} />

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            <strong>Error:</strong> {error}
          </div>
        )}

        {invoice && <AuditResult invoice={invoice} />}
      </main>
    </div>
  );
}
