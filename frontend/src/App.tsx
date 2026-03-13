import { useCallback, useState } from "react";
import Header from "./components/Header";
import PrivacyNotice from "./components/PrivacyNotice";
import FileUpload from "./components/FileUpload";
import AuditResult from "./components/AuditResult";
import AuditProgress from "./components/AuditProgress";
import ExampleInvoices from "./components/ExampleInvoices";
import InvoicePreview from "./components/InvoicePreview";
import { createAuditStream } from "./api";
import type { Invoice } from "./types";

export default function App() {
  const [uploading, setUploading] = useState(false);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<Record<string, "active" | "done">>({});
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setError(null);
    setInvoice(null);
    setSteps({});
    setStagedFile(null);
    setPreviewFile(null);

    try {
      await createAuditStream(
        file,
        (step, status) => setSteps((prev) => ({ ...prev, [step]: status })),
        (result) => {
          setInvoice(result);
          setPreviewFile(file);
          setSteps({});
        },
        (message) => {
          setError(message);
          setSteps({});
        },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setSteps({});
    } finally {
      setUploading(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <main className="flex-1 mx-auto max-w-4xl space-y-6 px-4 py-8">
        <PrivacyNotice />
        <ExampleInvoices onSelect={setStagedFile} disabled={uploading} />
        <FileUpload onUpload={handleUpload} disabled={uploading} stagedFile={stagedFile} />

        {uploading && Object.keys(steps).length > 0 && (
          <AuditProgress steps={steps} />
        )}

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
            <strong>Error:</strong> {error}
          </div>
        )}

        {invoice && <AuditResult invoice={invoice} />}
        {invoice && previewFile && <InvoicePreview file={previewFile} />}
      </main>
      <footer className="border-t border-gray-200 bg-white mt-auto">
        <div className="mx-auto max-w-4xl px-4 py-4 text-sm text-gray-500">
          © 2026 Frederik Wylich-Muxoll. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
