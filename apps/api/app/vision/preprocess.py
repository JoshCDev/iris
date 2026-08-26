"""Shared rice-leaf tensor recipe for training and ONNX serving.

Must match torchvision Resize(shorter-side=256) + CenterCrop(224) + ImageNet
normalize. Serving stays Pillow/numpy so the API does not import torch.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

INPUT_SIZE = 224
RESIZE_SHORT = 256
IMAGENET_MEAN = np.asarray([0.485, 0.456, 0.406], dtype="float32")
IMAGENET_STD = np.asarray([0.229, 0.224, 0.225], dtype="float32")


def resize_shorter_side(image: Image.Image, size: int = RESIZE_SHORT) -> Image.Image:
    width, height = image.size
    if width == 0 or height == 0:
        return image.resize((size, size), Image.BILINEAR)
    if width < height:
        new_w, new_h = size, max(1, int(round(height * size / width)))
    else:
        new_h, new_w = size, max(1, int(round(width * size / height)))
    return image.resize((new_w, new_h), Image.BILINEAR)


def center_crop(image: Image.Image, size: int = INPUT_SIZE) -> Image.Image:
    width, height = image.size
    left = max(0, (width - size) // 2)
    top = max(0, (height - size) // 2)
    cropped = image.crop((left, top, left + size, top + size))
    if cropped.size != (size, size):
        return cropped.resize((size, size), Image.BILINEAR)
    return cropped


def pil_to_nchw(image: Image.Image) -> Any:
    """RGB PIL image -> float32 NCHW batch of 1, ImageNet-normalized."""
    image = center_crop(resize_shorter_side(image.convert("RGB")))
    arr = np.asarray(image).astype("float32") / 255.0
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
    return np.transpose(arr, (2, 0, 1))[None, :, :, :]
