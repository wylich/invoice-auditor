"""Evaluate agent extraction quality against ground truth.

For each ground truth JSON in data/ground_truth/, runs the agent on the
corresponding invoice image, compares field-by-field, and prints an accuracy
report.
"""

import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import httpx
from pydantic import BaseModel
from pydantic_ai import BinaryContent

from invoice_auditor.agent.auditor import audit_agent, AuditDeps, QUALITY_THRESHOLD
from invoice_auditor.config import settings, PROJECT_ROOT
from invoice_auditor.core.schema import AuditResult
from invoice_auditor.core.vat_manager import VatManager
from invoice_auditor.core.cvr_manager import CvrManager
from invoice_auditor.processing.image import process_image, assess_image_quality
from invoice_auditor.processing.post_audit import infer_prices_include_vat

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

INVOICES_DIR = PROJECT_ROOT / "data" / "example_invoices"
GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
NUMBER_TOLERANCE = 0.02


# ── Result models ──────────────────────────────────────────────


class FieldResult(BaseModel):
    field: str
    expected: object
    actual: object
    match: bool


class InvoiceResult(BaseModel):
    filename: str
    field_results: list[FieldResult] = []

    @property
    def accuracy(self) -> float:
        if not self.field_results:
            return 0.0
        return sum(1 for r in self.field_results if r.match) / len(self.field_results)


# ── Comparison helpers ─────────────────────────────────────────


def strings_match(expected: str, actual: str) -> bool:
    return expected.strip().lower() == actual.strip().lower()


def numbers_match(expected: float, actual: float) -> bool:
    return abs(expected - actual) <= NUMBER_TOLERANCE


def optionals_match(expected: object, actual: object) -> bool:
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    if isinstance(expected, str) and isinstance(actual, str):
        return strings_match(expected, actual)
    return expected == actual


def compare_line_items(
    expected_items: list[dict],
    actual_items: list[dict],
) -> list[FieldResult]:
    results: list[FieldResult] = []
    max_len = max(len(expected_items), len(actual_items), 1)

    for i in range(max_len):
        prefix = f"line_items[{i}]"

        if i >= len(expected_items):
            results.append(FieldResult(
                field=prefix, expected="<missing>",
                actual=actual_items[i].get("description", "?"), match=False,
            ))
            continue
        if i >= len(actual_items):
            results.append(FieldResult(
                field=prefix, expected=expected_items[i].get("description", "?"),
                actual="<missing>", match=False,
            ))
            continue

        exp, act = expected_items[i], actual_items[i]

        # Description — case-insensitive, stripped
        results.append(FieldResult(
            field=f"{prefix}.description",
            expected=exp.get("description"),
            actual=act.get("description"),
            match=strings_match(
                str(exp.get("description", "")),
                str(act.get("description", "")),
            ),
        ))

        # Numeric fields (may be null for unreadable items)
        for num_field in ("quantity", "unit_price", "total_price", "vat_rate"):
            exp_raw = exp.get(num_field)
            act_raw = act.get(num_field)
            if exp_raw is None or act_raw is None:
                results.append(FieldResult(
                    field=f"{prefix}.{num_field}",
                    expected=exp_raw, actual=act_raw,
                    match=optionals_match(exp_raw, act_raw),
                ))
            else:
                results.append(FieldResult(
                    field=f"{prefix}.{num_field}",
                    expected=float(exp_raw), actual=float(act_raw),
                    match=numbers_match(float(exp_raw), float(act_raw)),
                ))

        # VAT category — exact (may be null)
        results.append(FieldResult(
            field=f"{prefix}.vat_category",
            expected=exp.get("vat_category"),
            actual=act.get("vat_category"),
            match=optionals_match(exp.get("vat_category"), act.get("vat_category")),
        ))

    return results


def compare_audit_results(expected: dict, actual: dict) -> list[FieldResult]:
    results: list[FieldResult] = []

    # String
    results.append(FieldResult(
        field="vendor_name",
        expected=expected["vendor_name"], actual=actual["vendor_name"],
        match=strings_match(expected["vendor_name"], actual["vendor_name"]),
    ))

    # Optional string
    results.append(FieldResult(
        field="vendor_cvr",
        expected=expected.get("vendor_cvr"), actual=actual.get("vendor_cvr"),
        match=optionals_match(expected.get("vendor_cvr"), actual.get("vendor_cvr")),
    ))

    # Date — exact
    results.append(FieldResult(
        field="invoice_date",
        expected=expected["invoice_date"], actual=actual["invoice_date"],
        match=expected["invoice_date"] == actual["invoice_date"],
    ))

    # Optional time
    results.append(FieldResult(
        field="invoice_time",
        expected=expected.get("invoice_time"), actual=actual.get("invoice_time"),
        match=optionals_match(expected.get("invoice_time"), actual.get("invoice_time")),
    ))

    # Currency — exact
    results.append(FieldResult(
        field="currency",
        expected=expected["currency"], actual=actual["currency"],
        match=expected["currency"] == actual["currency"],
    ))

    # Boolean
    results.append(FieldResult(
        field="prices_include_vat",
        expected=expected["prices_include_vat"], actual=actual["prices_include_vat"],
        match=expected["prices_include_vat"] == actual["prices_include_vat"],
    ))

    # Numbers
    for num_field in ("total_amount_raw", "total_vat_raw"):
        results.append(FieldResult(
            field=num_field,
            expected=expected[num_field], actual=actual[num_field],
            match=numbers_match(expected[num_field], actual[num_field]),
        ))

    # Line items
    results.extend(compare_line_items(
        expected.get("line_items", []),
        actual.get("line_items", []),
    ))

    return results


# ── Agent runner ───────────────────────────────────────────────


async def extract_audit_result(image_path: Path) -> AuditResult:
    """Run the agent on a single image and return the AuditResult.

    Mirrors the production pipeline: quality assessment, prompt warning,
    and prices_include_vat correction.
    """
    with open(image_path, "rb") as f:
        quality_score = assess_image_quality(f)
        image_bytes, media_type = process_image(f)

    logger.info("Image quality score: %.2f", quality_score)

    prompt = "Audit this invoice image. Extract all data, use lookup_vat for each line item, and validate_cvr if a CVR is visible."
    if quality_score < QUALITY_THRESHOLD:
        prompt = (
            f"WARNING: This image has been assessed as low quality (score: {quality_score:.2f}/1.00). "
            "Be extra cautious — set ai_confidence low and set any unreadable fields to null.\n\n"
            + prompt
        )

    async with httpx.AsyncClient(timeout=5.0) as client:
        deps = AuditDeps(
            vat_manager=VatManager(),
            cvr_manager=CvrManager(),
            http_client=client,
        )
        result = await audit_agent.run(
            [
                prompt,
                BinaryContent(data=image_bytes, media_type=media_type),
            ],
            deps=deps,
            model=settings.openai.model,
        )

    audit_result = result.output

    # Apply the same prices_include_vat correction as production
    inferred = infer_prices_include_vat(
        audit_result.line_items, audit_result.total_amount_raw, audit_result.total_vat_raw,
    )
    if inferred is not None and inferred != audit_result.prices_include_vat:
        logger.info(
            "Correcting prices_include_vat: %s → %s",
            audit_result.prices_include_vat, inferred,
        )
        audit_result.prices_include_vat = inferred

    return audit_result


# ── Report printing ────────────────────────────────────────────


def print_report(invoice_results: list[InvoiceResult]):
    total_fields = 0
    total_matches = 0

    for inv in invoice_results:
        matched = sum(1 for r in inv.field_results if r.match)
        total_fields += len(inv.field_results)
        total_matches += matched

        print(f"\n{'=' * 60}")
        print(f"  {inv.filename}  --  {inv.accuracy:.0%} accuracy")
        print(f"{'=' * 60}")

        for r in inv.field_results:
            if not r.match:
                print(f"  x  {r.field}")
                print(f"       expected: {r.expected}")
                print(f"       actual:   {r.actual}")

        print(f"  {matched}/{len(inv.field_results)} fields correct")

    overall = total_matches / total_fields if total_fields else 0
    print(f"\n{'=' * 60}")
    print(f"  OVERALL: {total_matches}/{total_fields} fields correct ({overall:.0%})")
    print(f"{'=' * 60}\n")


# ── Main ───────────────────────────────────────────────────────


async def main():
    ground_truth_files = sorted(GROUND_TRUTH_DIR.glob("*.json"))

    if not ground_truth_files:
        logger.error("No ground truth files found in %s", GROUND_TRUTH_DIR)
        logger.error("Run generate_ground_truth.py first.")
        return

    invoice_results: list[InvoiceResult] = []

    for gt_path in ground_truth_files:
        # Find the matching image file
        image_path = None
        for ext in IMAGE_EXTENSIONS:
            candidate = INVOICES_DIR / f"{gt_path.stem}{ext}"
            if candidate.exists():
                image_path = candidate
                break

        if image_path is None:
            logger.warning("No image found for %s, skipping", gt_path.name)
            continue

        logger.info("Evaluating %s ...", image_path.name)

        expected = json.loads(gt_path.read_text(encoding="utf-8"))

        try:
            audit_result = await extract_audit_result(image_path)
            actual = audit_result.model_dump(mode="json")
        except Exception:
            logger.exception("Agent failed on %s", image_path.name)
            continue

        field_results = compare_audit_results(expected, actual)
        invoice_results.append(InvoiceResult(
            filename=image_path.name, field_results=field_results,
        ))

    if invoice_results:
        print_report(invoice_results)


if __name__ == "__main__":
    asyncio.run(main())
