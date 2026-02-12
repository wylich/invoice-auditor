from invoice_auditor.core.schema import Invoice
from invoice_auditor.core.vat_manager import VatManager


def verify_vat_math(invoice: Invoice, vat_manager: VatManager):
    """Checks if the extracted VAT makes sense mathematically and legally."""
    calculated_vat = 0.0

    for item in invoice.line_items:
        rule_rate, _, reason = vat_manager.lookup_item(item.description)

        if item.vat_rate != rule_rate:
            invoice.add_flag(
                category="Data Integrity",
                severity="Medium",
                message=f"VAT Mismatch on '{item.description}'. AI saw {item.vat_rate*100}%, but rule '{reason}' expects {rule_rate*100}%."
            )

        if invoice.prices_include_vat:
            calculated_vat += item.total_price / (1 + item.vat_rate) * item.vat_rate
        else:
            calculated_vat += item.total_price * item.vat_rate

    if abs(calculated_vat - invoice.total_vat_raw) > 0.05:
        invoice.add_flag(
            category="Data Integrity",
            severity="High",
            message=f"Math Error: Line items sum to {calculated_vat:.2f} VAT, but invoice total says {invoice.total_vat_raw:.2f}."
        )


def handle_currency(invoice: Invoice):
    """Handles currency conversion flagging."""
    if invoice.currency != "DKK":
        invoice.total_amount_dkk = invoice.total_amount_raw * invoice.exchange_rate_used
        invoice.add_flag("Forex", "Low", f"Converted from {invoice.currency} (Rate: {invoice.exchange_rate_used})")
    else:
        invoice.total_amount_dkk = invoice.total_amount_raw


def assign_status(invoice: Invoice):
    """Assigns final audit status based on flags."""
    if invoice.audit_flags:
        invoice.status = "Red" if any(f.severity == "High" for f in invoice.audit_flags) else "Review"
    else:
        invoice.status = "Green"
