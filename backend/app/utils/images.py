"""Image validation (by content, not extension) and perceptual hashing."""
from __future__ import annotations

import hashlib
import io

import imagehash
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import ValidationFailure

_FORMAT_META = {
    "PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"), "WEBP": ("image/webp", "webp"), "GIF": ("image/gif", "gif"),
}
HASH_BITS = 64


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_image(data: bytes) -> dict:
    """Validate the actual bytes with Pillow. Raises ValidationFailure on anything unsafe or unsupported."""
    s = get_settings()
    if not data:
        raise ValidationFailure("Empty file")
    if len(data) > s.max_upload_bytes:
        raise ValidationFailure(f"File exceeds the {s.max_upload_bytes} byte limit", status_code=413, code="payload_too_large")
    Image.MAX_IMAGE_PIXELS = s.max_image_pixels  # guards against decompression bombs
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = (probe.format or "").upper()
            width, height = probe.size
            probe.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError):
        raise ValidationFailure("File is not a valid image")
    if fmt not in s.allowed_image_formats or fmt not in _FORMAT_META:
        raise ValidationFailure(f"Image format {fmt or 'unknown'} is not permitted (allowed: {', '.join(s.allowed_image_formats)})")
    if width * height > s.max_image_pixels:
        raise ValidationFailure("Image dimensions are too large")
    content_type, ext = _FORMAT_META[fmt]
    return {"format": fmt, "content_type": content_type, "extension": ext, "width": width, "height": height}


def perceptual_hash(data: bytes) -> str:
    """64-bit DCT perceptual hash as 16 hex chars. Re-opens the image (verify() invalidates the first handle)."""
    with Image.open(io.BytesIO(data)) as im:
        im.seek(0)
        return str(imagehash.phash(im.convert("RGB"), hash_size=8))


def is_valid_phash(value: str | None) -> bool:
    if not value or len(value) != 16:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")
