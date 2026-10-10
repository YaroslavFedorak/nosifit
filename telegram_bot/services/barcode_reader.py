"""Reads a retail barcode from a photo, locally and in memory.

The photo bytes come straight from Telegram into memory, are decoded here
(zxing-cpp, via Pillow) and dropped: nothing is written to disk, logged or
sent anywhere else. Only the decoded digits leave this module.

Limits keep a hostile file from costing much: a byte cap before decoding,
an image-type allow list (JPEG/PNG/WebP, checked from the content, not the
name) and a pixel cap checked from the header before pixels are decoded.
"""

from __future__ import annotations

import io
import logging
import warnings

from backend.app.services.nutrition.barcode import InvalidBarcode, normalize_barcode

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
# Large photos are scaled down first: a barcode stays readable and decoding
# a 12-megapixel photo would just cost time.
MAX_SIDE = 2000
ALLOWED_FORMATS = ("JPEG", "PNG", "WEBP")
ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class BarcodeImageError(ValueError):
    """The file is not an image we accept (type or size)."""


def decode_barcode(data: bytes) -> str | None:
    """Canonical GTIN found in the image, or None when there is none."""
    if not data:
        raise BarcodeImageError("empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise BarcodeImageError("too_large")

    import zxingcpp
    from PIL import Image

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=ALLOWED_FORMATS) as image:
                width, height = image.size
                if width * height > MAX_PIXELS:
                    raise BarcodeImageError("too_many_pixels")
                if image.format == "JPEG":
                    # Decode JPEGs at reduced size directly (cheap).
                    image.draft("L", (MAX_SIDE, MAX_SIDE))
                gray = image.convert("L")
    except BarcodeImageError:
        raise
    except Exception as exc:  # unreadable, truncated or not an allowed type
        logger.info("Barcode photo rejected: %s", type(exc).__name__)
        raise BarcodeImageError("unreadable")

    try:
        if max(gray.size) > MAX_SIDE:
            gray.thumbnail((MAX_SIDE, MAX_SIDE))
        results = zxingcpp.read_barcodes(
            gray,
            formats=zxingcpp.BarcodeFormat.EANUPC,
        )
    finally:
        gray.close()

    for result in results:
        text = result.text or ""
        if result.format == zxingcpp.BarcodeFormat.UPCE:
            # UPC-E is a compressed UPC-A; the database knows the long form.
            text = _expand_upce(text)
        try:
            return normalize_barcode(text)
        except InvalidBarcode:
            continue
    return None


def _expand_upce(code: str) -> str:
    """UPC-E (8 digits with number system and check digit) -> UPC-A."""
    if len(code) != 8 or not code.isdigit():
        return code
    system, body, check = code[0], code[1:7], code[7]
    last = body[5]
    if last in "012":
        middle = body[0:2] + last + "0000" + body[2:5]
    elif last == "3":
        middle = body[0:3] + "00000" + body[3:5]
    elif last == "4":
        middle = body[0:4] + "00000" + body[4]
    else:
        middle = body[0:5] + "0000" + last
    return system + middle + check
