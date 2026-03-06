type StepStatus = "active" | "done";

interface AuditProgressProps {
  steps: Record<string, StepStatus>;
}

const STEP_ORDER = ["image", "extraction", "vat", "cvr", "finalizing"];
const STEP_LABELS: Record<string, string> = {
  image: "Processing image",
  extraction: "Extracting invoice data",
  vat: "Looking up VAT rates",
  cvr: "Validating CVR number",
  finalizing: "Finalising audit",
};

export default function AuditProgress({ steps }: AuditProgressProps) {
  const visibleSteps = STEP_ORDER.filter((s) => s in steps);

  if (visibleSteps.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <ul className="space-y-2">
        {visibleSteps.map((step) => {
          const status = steps[step];
          return (
            <li key={step} className="flex items-center gap-3 text-sm">
              {status === "done" ? (
                <span className="text-green-500 font-bold">✓</span>
              ) : (
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
              )}
              <span className={status === "done" ? "text-gray-500" : "text-gray-900 font-medium"}>
                {STEP_LABELS[step] ?? step}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
