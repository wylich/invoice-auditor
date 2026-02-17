export default function PrivacyNotice() {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <strong>Privacy notice:</strong> Uploaded images are sent to OpenAI for
      processing. No data is persisted on the server after the response is
      returned. Do not upload documents containing sensitive personal
      information.
    </div>
  );
}
