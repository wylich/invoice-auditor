export default function Header() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto max-w-4xl px-4 py-4">
        <h1 className="text-xl font-semibold text-gray-900">
          Invoice Auditor
        </h1>
        <p className="text-sm text-gray-500">
          Upload a receipt to extract and audit invoice data
        </p>
      </div>
    </header>
  );
}
