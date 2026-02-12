import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)


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
