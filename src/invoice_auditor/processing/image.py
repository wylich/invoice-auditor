import io
import logging
from typing import Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageStat

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}
MAX_SIZE = (2048, 2048)


def assess_image_quality(file_object) -> float:
    """Assess image quality on a 0.0–1.0 scale based on sharpness, contrast, and resolution.

    For invoice/document images, resolution is the strongest predictor of readability.
    Resets the file position after reading so the file can be reused.
    """
    image = Image.open(file_object)
    gray = image.convert("L")

    # Sharpness: std-dev of edge-detected image (higher = sharper)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    sharpness = ImageStat.Stat(edges).stddev[0]

    # Contrast: std-dev of grayscale pixel values (higher = more contrast)
    contrast = ImageStat.Stat(gray).stddev[0]

    # Resolution: smallest dimension
    min_dim = min(image.size)

    sharpness_score = min(sharpness / 50.0, 1.0)
    contrast_score = min(contrast / 50.0, 1.0)
    resolution_score = min(min_dim / 800.0, 1.0)

    score = 0.2 * sharpness_score + 0.3 * contrast_score + 0.5 * resolution_score

    file_object.seek(0)
    logger.debug(
        "Image quality: sharpness=%.1f, contrast=%.1f, min_dim=%d, score=%.2f",
        sharpness, contrast, min_dim, score,
    )
    return score


def process_image(file_object) -> Tuple[bytes, str]:
    """Normalizes an input image for the vision API.

    Preserves the original format when the API supports it (JPEG, PNG, WebP, GIF).
    Only converts to JPEG as a fallback for unsupported formats (e.g. AVIF, TIFF).
    Returns (image_bytes, media_type).
    """
    try:
        image = Image.open(file_object)
        original_format = image.format

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        image.thumbnail(MAX_SIZE)

        if original_format in SUPPORTED_FORMATS:
            output_format = original_format
        else:
            output_format = "JPEG"

        buffer = io.BytesIO()
        image.save(buffer, format=output_format, quality=85)
        buffer.seek(0)

        media_type = SUPPORTED_FORMATS.get(output_format, "image/jpeg")
        return buffer.read(), media_type

    except Exception as e:
        logger.error("Image processing failed: %s", e)
        raise ValueError("Could not process image. File might be corrupted or unsupported.") from e


def pdf_to_images(file_object) -> list[Tuple[bytes, str]]:
    """Convert all pages of a PDF to JPEG images.

    Returns a list of (image_bytes, media_type) tuples, one per page.
    """
    file_object.seek(0)
    pdf = fitz.open(stream=file_object.read(), filetype="pdf")
    pages = []
    for page in pdf:
        pix = page.get_pixmap(dpi=150)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image.thumbnail(MAX_SIZE)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        pages.append((buffer.getvalue(), "image/jpeg"))
    logger.info("PDF converted: %d page(s)", len(pages))
    return pages
