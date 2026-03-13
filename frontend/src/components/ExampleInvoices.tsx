const EXAMPLES = [
  { path: "/examples/invoice5.jpg", label: "Invoice A", mimeType: "image/jpeg" },
  { path: "/examples/invoice4.png", label: "Invoice B", mimeType: "image/png" },
  { path: "/examples/invoice6.jpg", label: "Invoice C", mimeType: "image/jpeg" },
];

interface ExampleInvoicesProps {
  onSelect: (file: File) => void;
  disabled: boolean;
}

export default function ExampleInvoices({ onSelect, disabled }: ExampleInvoicesProps) {
  async function handleClick(example: (typeof EXAMPLES)[number]) {
    const res = await fetch(example.path);
    const blob = await res.blob();
    const filename = example.path.split("/").pop()!;
    const file = new File([blob], filename, { type: example.mimeType });
    onSelect(file);
  }

  return (
    <div>
      <p className="mb-2 text-sm text-gray-500">Don't have an invoice to audit? Try an example here:</p>
      <div className="flex gap-3">
        {EXAMPLES.map((ex) => (
          <button
            key={ex.path}
            onClick={() => handleClick(ex)}
            disabled={disabled}
            className="flex flex-col items-center rounded-lg border border-gray-200 bg-white p-2 transition-colors hover:border-gray-400 disabled:pointer-events-none disabled:opacity-40"
          >
            <img
              src={ex.path}
              alt={ex.label}
              className="h-20 w-16 rounded object-cover"
            />
            <p className="mt-1 text-xs text-gray-500">{ex.label}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
