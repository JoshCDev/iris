from pathlib import Path

from PIL import Image

from app.vision.preprocess import INPUT_SIZE, pil_to_nchw, resize_shorter_side


def test_pil_to_nchw_shape_and_dtype():
    img = Image.new("RGB", (640, 480), (20, 180, 40))
    arr = pil_to_nchw(img)
    assert arr.shape == (1, 3, INPUT_SIZE, INPUT_SIZE)
    assert arr.dtype == "float32"


def test_resize_shorter_side_keeps_aspect():
    img = Image.new("RGB", (400, 200), (0, 0, 0))
    out = resize_shorter_side(img, 256)
    assert min(out.size) == 256
    assert out.size[0] / out.size[1] == 400 / 200
