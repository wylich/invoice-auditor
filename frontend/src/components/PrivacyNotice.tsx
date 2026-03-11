export default function PrivacyNotice() {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <strong>Privacy notice:</strong> Invoices are sent to OpenAI for
      processing. 
      OpenAI retains API data for up to 30 days for safety
      monitoring, but does not use it for model training. 
      No data is stored on this server after processing. <br />
      Ensure you have a legal basis for sharing any personal 
      data with a third-party processor (e.g. GDPR compliance).
    </div>
  );
}


// to add a newline you use <br />