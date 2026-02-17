import type { Invoice, AuditFlag } from "../types";

const STATUS_COLORS: Record<string, string> = {
  Green: "bg-green-100 text-green-800",
  Review: "bg-yellow-100 text-yellow-800",
  Red: "bg-red-100 text-red-800",
  Pending: "bg-gray-100 text-gray-800",
};

const SEVERITY_COLORS: Record<string, string> = {
  Low: "border-yellow-300 bg-yellow-50",
  Medium: "border-orange-300 bg-orange-50",
  High: "border-red-300 bg-red-50",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-sm font-medium ${STATUS_COLORS[status] ?? STATUS_COLORS.Pending}`}
    >
      {status}
    </span>
  );
}

function FlagCard({ flag }: { flag: AuditFlag }) {
  return (
    <div
      className={`rounded-lg border p-3 ${SEVERITY_COLORS[flag.severity] ?? ""}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-600">
          {flag.category}
        </span>
        <span className="text-xs text-gray-500">
          {flag.severity} {flag.is_resolved ? "— Resolved" : ""}
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-800">{flag.message}</p>
    </div>
  );
}

function formatAmount(value: number): string {
  return value.toLocaleString("da-DK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatConfidence(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function formatVatRate(rate: number | null): string {
  if (rate == null) return "—";
  return `${(rate * 100).toFixed(0)}%`;
}

export default function AuditResult({ invoice }: { invoice: Invoice }) {
  return (
    <div className="space-y-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      {/* Header row */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {invoice.vendor_name}
          </h2>
          {invoice.vendor_cvr && (
            <p className="text-sm text-gray-500">CVR: {invoice.vendor_cvr}</p>
          )}
        </div>
        <StatusBadge status={invoice.status} />
      </div>

      {/* Summary grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCell label="Date" value={invoice.invoice_date} />
        <SummaryCell
          label="Total"
          value={`${formatAmount(invoice.total_amount_raw)} ${invoice.currency}`}
        />
        <SummaryCell
          label="VAT"
          value={`${formatAmount(invoice.total_vat_raw)} ${invoice.currency}`}
        />
        <SummaryCell
          label="Total (DKK)"
          value={formatAmount(invoice.total_amount_dkk)}
        />
      </div>

      {invoice.currency !== "DKK" && (
        <p className="text-xs text-gray-500">
          Exchange rate: 1 {invoice.currency} = {invoice.exchange_rate_used} DKK
        </p>
      )}

      {/* Line items */}
      {invoice.line_items.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">
            Line items
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                  <th className="pb-2 pr-4">Description</th>
                  <th className="pb-2 pr-4 text-right">Qty</th>
                  <th className="pb-2 pr-4 text-right">Unit price</th>
                  <th className="pb-2 pr-4 text-right">Total</th>
                  <th className="pb-2 pr-4 text-right">VAT</th>
                  <th className="pb-2 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items.map((item, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-2 pr-4 text-gray-800">
                      {item.description}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-600">
                      {item.quantity}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-600">
                      {item.unit_price != null ? formatAmount(item.unit_price) : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-600">
                      {item.total_price != null ? formatAmount(item.total_price) : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right text-gray-600">
                      {formatVatRate(item.vat_rate)}
                    </td>
                    <td className="py-2 text-right text-gray-600">
                      {formatConfidence(item.ai_confidence)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Audit flags */}
      {invoice.audit_flags.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">
            Audit flags
          </h3>
          <div className="space-y-2">
            {invoice.audit_flags.map((flag, i) => (
              <FlagCard key={i} flag={flag} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium text-gray-900">{value}</p>
    </div>
  );
}
