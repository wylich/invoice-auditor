import io
import json
import logging
import uuid

import httpx
from PIL import Image
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, BinaryContent

from invoice_auditor.agent.prompt import SYSTEM_PROMPT
from invoice_auditor.core.schema import Invoice, AuditResult
from invoice_auditor.core.vat_manager import VatManager
from invoice_auditor.api.cvr_manager import CvrManager

logger = logging.getLogger(__name__)



class AuditDeps(BaseModel):
    """Runtime dependencies injected into the agent."""
    vat_manager: VatManager
    cvr_manager: CvrManager
    http_client: httpx.AsyncClient

    model_config = {"arbitrary_types_allowed": True}


audit_agent = Agent(
    deps_type=AuditDeps,
    output_type=AuditResult,
    system_prompt=SYSTEM_PROMPT,
    )


@audit_agent.tool
async def lookup_vat(ctx: RunContext[AuditDeps], item_description: str) -> str:
    """Look up the correct VAT rate for a line item description.

    Args:
        item_description: The product/service description from the receipt.
    """
    rate, category, reason = ctx.deps.vat_manager.lookup_item(item_description)
    logger.debug("lookup_vat(%s) -> %.0f%% %s (%s)", item_description, rate * 100, category, reason)
    return f"VAT rate: {rate*100}%, category: {category}, reason: {reason}"


@audit_agent.tool
async def validate_cvr(ctx: RunContext[AuditDeps], cvr_number: str) -> str:
    """Validate a Danish CVR number against the business registry.

    Args:
        cvr_number: The 8-digit Danish CVR number to validate.
    """
    result = await ctx.deps.cvr_manager.validate_cvr(cvr_number, ctx.deps.http_client)
    logger.debug("validate_cvr(%s) -> valid=%s, risk=%s", cvr_number, result.get("valid"), result.get("risk_level"))
    return json.dumps(result)


def process_image(file_object) -> bytes:
    """Standardizes input images (AVIF, WebP, PNG) to JPEG bytes."""
    try:
        image = Image.open(file_object)

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        max_size = (1024, 1024)
        image.thumbnail(max_size)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        return buffer.read()

    except Exception as e:
        logger.error("Image processing failed: %s", e)
        raise ValueError("Could not process image. File might be corrupted or unsupported.") from e


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


async def run_audit(image_file, filename: str) -> Invoice:
    """Entry point: preprocess image, run agent, post-process, return Invoice."""
    logger.info("Starting audit for %s", filename)

    image_bytes = process_image(image_file)
    logger.info("Image preprocessed (%d bytes JPEG)", len(image_bytes))

    async with httpx.AsyncClient(timeout=5.0) as client:
        deps = AuditDeps(
            vat_manager=VatManager(),
            cvr_manager=CvrManager(),
            http_client=client,
        )

        logger.info("Running agent extraction...")
        try:
            result = await audit_agent.run(
                [
                    "Audit this invoice image. Extract all data, use lookup_vat for each line item, and validate_cvr if a CVR is visible.",
                    BinaryContent(data=image_bytes, media_type="image/jpeg"),
                ],
                deps=deps,
                model="openai:gpt-4o-mini",
            )
        except Exception:
            logger.exception("Agent run failed for %s", filename)
            raise

    audit_result = result.output
    logger.info(
        "Agent extracted: vendor=%s, cvr=%s, %d line items, total=%.2f %s",
        audit_result.vendor_name,
        audit_result.vendor_cvr,
        len(audit_result.line_items),
        audit_result.total_amount_raw,
        audit_result.currency,
    )

    invoice = Invoice(
        id=str(uuid.uuid4()),
        filename=filename,
        total_amount_dkk=audit_result.total_amount_raw,
        **audit_result.model_dump(),
    )

    verify_vat_math(invoice, deps.vat_manager)
    handle_currency(invoice)
    assign_status(invoice)

    logger.info("Audit complete for %s: status=%s, flags=%d", filename, invoice.status, len(invoice.audit_flags))
    return invoice
