import io

import pytest
from PIL import Image

from app.vision.image_guard import ImageGuardService, ImageRejectedError

guard = ImageGuardService()


def _png_bytes(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 180, 90)).save(buf, "PNG")
    return buf.getvalue()


def test_rejects_oversized_bytes():
    with pytest.raises(ImageRejectedError) as ei:
        guard.validate_upload(b"x" * (8 * 1024 * 1024 + 1))
    assert ei.value.code == "upload_too_large"


def test_rejects_excessive_pixels():
    big = _png_bytes(6000, 4000)  # 24 MP > 20 MP cap
    with pytest.raises(ImageRejectedError) as ei:
        guard.validate_upload(big)
    assert ei.value.code == "image_too_many_pixels"


def test_accepts_normal_photo():
    guard.validate_upload(_png_bytes(800, 600))
