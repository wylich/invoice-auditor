import logging
from typing import List

from invoice_auditor.core.schema import Invoice, LineItem
from invoice_auditor.core.vat_manager import VatManager

logger = logging.getLogger(__name__)

SUBTOTAL_TOLERANCE = 1.0


def infer_prices_include_vat(
    line_items: List[LineItem],
    total_amount_raw: float,
    total_vat_raw: float,
) -> bool | None:
    """Infer whether prices include VAT by checking which interpretation makes the math work.

    Returns True (inclusive), False (exclusive), or None if neither matches.
    """
    items_total = sum(item.total_price for item in line_items if item.total_price is not None)

    if items_total == 0:
        return None

    # If line items ≈ total → prices include VAT
    inclusive_diff = abs(items_total - total_amount_raw)
    # If line items ≈ total - vat → prices exclude VAT
    exclusive_diff = abs(items_total - (total_amount_raw - total_vat_raw))

    if inclusive_diff <= SUBTOTAL_TOLERANCE and exclusive_diff > SUBTOTAL_TOLERANCE:
        return True
    if exclusive_diff <= SUBTOTAL_TOLERANCE and inclusive_diff > SUBTOTAL_TOLERANCE:
        return False

    return None


def correct_prices_include_vat(invoice: Invoice):
    """Override prices_include_vat if the math clearly indicates the agent got it wrong."""
    inferred = infer_prices_include_vat(
        invoice.line_items, invoice.total_amount_raw, invoice.total_vat_raw,
    )
    if inferred is not None and inferred != invoice.prices_include_vat:
        logger.info(
            "Correcting prices_include_vat: %s → %s (based on line item math)",
            invoice.prices_include_vat, inferred,
        )
        invoice.prices_include_vat = inferred


def verify_vat_math(invoice: Invoice, vat_manager: VatManager):
    """Checks if the extracted VAT makes sense mathematically and legally."""
    calculated_vat = 0.0
    line_items_total = 0.0
    has_incomplete_items = False

    for item in invoice.line_items:
        if item.total_price is None or item.vat_rate is None:
            has_incomplete_items = True
            invoice.add_flag(
                category="Data Integrity",
                severity="High",
                message=f"Missing price data for '{item.description}'. Cannot verify VAT.",
            )
            continue

        rule_rate, _, reason = vat_manager.lookup_item(item.description)

        if item.vat_rate != rule_rate:
            invoice.add_flag(
                category="Data Integrity",
                severity="Medium",
                message=f"VAT Mismatch on '{item.description}'. AI saw {item.vat_rate*100}%, but rule '{reason}' expects {rule_rate*100}%."
            )

        line_items_total += item.total_price

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

    # Subtotal check: do line item totals add up to the invoice total?
    if invoice.prices_include_vat:
        expected_subtotal = invoice.total_amount_raw
    else:
        expected_subtotal = invoice.total_amount_raw - invoice.total_vat_raw

    if abs(line_items_total - expected_subtotal) > 0.05:
        detail = " (some items have missing prices)" if has_incomplete_items else ""
        invoice.add_flag(
            category="Data Integrity",
            severity="High",
            message=f"Math Error: Line items sum to {line_items_total:.2f}, but expected subtotal is {expected_subtotal:.2f}.{detail}",
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
