import io
import logging
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}
MAX_SIZE = (2048, 2048)


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
