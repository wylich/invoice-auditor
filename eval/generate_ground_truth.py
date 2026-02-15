"""Generate ground truth seed files by running the agent on example invoices.

Runs the extraction agent on each image in data/example_invoices/ and saves
the raw AuditResult as JSON to data/ground_truth/<stem>.json.

Existing ground truth files are skipped — delete them to regenerate.
"""

import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import httpx
from pydantic_ai import BinaryContent

from invoice_auditor.agent.auditor import audit_agent, AuditDeps
from invoice_auditor.config import settings, PROJECT_ROOT
from invoice_auditor.core.schema import AuditResult
from invoice_auditor.core.vat_manager import VatManager
from invoice_auditor.core.cvr_manager import CvrManager
from invoice_auditor.processing.image import process_image

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

INVOICES_DIR = PROJECT_ROOT / "data" / "example_invoices"
GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


async def extract_audit_result(image_path: Path) -> AuditResult:
    """Run the agent on a single image and return the AuditResult."""
    with open(image_path, "rb") as f:
        image_bytes, media_type = process_image(f)

    async with httpx.AsyncClient(timeout=5.0) as client:
        deps = AuditDeps(
            vat_manager=VatManager(),
            cvr_manager=CvrManager(),
            http_client=client,
        )
        result = await audit_agent.run(
            [
                "Audit this invoice image. Extract all data, use lookup_vat for each line item, and validate_cvr if a CVR is visible.",
                BinaryContent(data=image_bytes, media_type=media_type),
            ],
            deps=deps,
            model=settings.openai.model,
        )
    return result.output


async def main():
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        p for p in INVOICES_DIR.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        logger.error("No images found in %s", INVOICES_DIR)
        return

    for image_path in image_files:
        output_path = GROUND_TRUTH_DIR / f"{image_path.stem}.json"
        if output_path.exists():
            logger.info("Skipping %s (ground truth already exists)", image_path.name)
            continue

        logger.info("Processing %s ...", image_path.name)
        try:
            audit_result = await extract_audit_result(image_path)
            output_path.write_text(
                json.dumps(audit_result.model_dump(mode="json"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("Saved ground truth -> %s", output_path.name)
        except Exception:
            logger.exception("Failed to process %s", image_path.name)


if __name__ == "__main__":
    asyncio.run(main())
