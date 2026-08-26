from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image


@dataclass
class ImageGuardResult:
    width: int
    height: int
    metrics: dict[str, float]


class ImageRejectedError(ValueError):
    def __init__(self, *, code: str, message: str, metrics: dict[str, float], retry_guidance: list[str]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.metrics = metrics
        self.retry_guidance = retry_guidance


class ImageGuardService:
    min_size = 80

    def analyze(self, image_bytes: bytes) -> ImageGuardResult:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise ImageRejectedError(
                code="unreadable_image",
                message="The file could not be read as a photo.",
                metrics={},
                retry_guidance=["Upload a JPG, PNG, or WebP image.", "Retake the photo if the file came from a camera app."],
            ) from exc

        width, height = image.size
        if width < self.min_size or height < self.min_size:
            raise ImageRejectedError(
                code="image_too_small",
                message="The photo is too small for a reliable leaf check.",
                metrics={"width": float(width), "height": float(height)},
                retry_guidance=["Use a clearer photo where the leaf fills most of the frame."],
            )

        small = image.resize((224, 224))
        arr = np.asarray(small, dtype=np.float32) / 255.0
        red, green, blue = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        channel_std = float(arr.reshape(-1, 3).std(axis=0).mean())
        luminance_std = float(luminance.std())
        dynamic_range = float(np.percentile(luminance, 99) - np.percentile(luminance, 1))
        entropy = self._entropy(luminance)
        edge_density = self._edge_density(luminance)
        saturation = self._saturation(arr)
        mean_saturation = float(saturation.mean())
        plant_mask = self._plant_mask(red, green, blue, luminance, saturation)
        plant_like_ratio = float(plant_mask.mean())
        green_dominance = self._green_dominance(red, green, blue)
        color_diversity = self._color_diversity(arr)
        largest_blob_ratio, blob_count = self._connected_components(plant_mask)

        metrics = {
            "width": float(width),
            "height": float(height),
            "luminance_std": round(luminance_std, 4),
            "channel_std": round(channel_std, 4),
            "dynamic_range": round(dynamic_range, 4),
            "entropy": round(entropy, 4),
            "edge_density": round(edge_density, 4),
            "plant_like_ratio": round(plant_like_ratio, 4),
            "mean_saturation": round(mean_saturation, 4),
            "green_dominance": round(green_dominance, 4),
            "color_diversity": round(color_diversity, 4),
            "largest_blob_ratio": round(largest_blob_ratio, 4),
            "blob_count": float(blob_count),
        }

        # Gate 1: Blank or solid images
        if luminance_std < 0.018 or channel_std < 0.015 or dynamic_range < 0.055 or entropy < 1.15:
            raise ImageRejectedError(
                code="blank_or_solid_image",
                message="This image looks blank or nearly solid, so the rice leaf model cannot evaluate it.",
                metrics=metrics,
                retry_guidance=[
                    "Upload a real rice leaf photo with visible texture and natural lighting.",
                    "Keep the leaf in focus and avoid screenshots, black frames, or solid-color test images.",
                ],
            )

        # Gate 2: Non-plant image - STRICT multi-tier check
        # Tier A: Very low plant-like ratio -> definitely not a plant
        if plant_like_ratio < 0.08:
            raise ImageRejectedError(
                code="non_leaf_or_non_plant_image",
                message="This image does not appear to contain a rice leaf. IRIS only analyzes rice leaf photos.",
                metrics=metrics,
                retry_guidance=[
                    "Take a close-up photo of the rice leaf.",
                    "Make sure the leaf fills most of the frame with good lighting.",
                    "Avoid uploading photos of non-plant subjects.",
                ],
            )

        # Tier B: Moderate plant-like ratio but suspicious characteristics
        if plant_like_ratio < 0.20:
            if green_dominance < 0.12 and mean_saturation < 0.18:
                raise ImageRejectedError(
                    code="non_leaf_or_non_plant_image",
                    message="This image does not look like a usable rice leaf photo. The model needs a clear view of leaf tissue.",
                    metrics=metrics,
                    retry_guidance=[
                        "Retake the photo close to the rice leaf.",
                        "Include the leaf surface and symptom area in the frame.",
                        "Use natural daylight for best results.",
                    ],
                )

        # Tier C: Borderline plant ratio - need texture evidence
        if plant_like_ratio < 0.30 and edge_density < 0.08 and mean_saturation < 0.12:
            raise ImageRejectedError(
                code="non_leaf_or_non_plant_image",
                message="This photo may not contain enough visible leaf tissue for reliable analysis.",
                metrics=metrics,
                retry_guidance=[
                    "Move closer to the leaf so it fills more of the frame.",
                    "Ensure the leaf is in focus with visible veins and texture.",
                ],
            )

        # Gate 3: GREEN DOMINANCE CHECK - the most critical gate.
        # Real plant photos MUST have significant green-channel presence.
        # Severely diseased leaves AND leaves held in a hand can drop the global
        # green ratio; allow them through when BOTH plant texture AND blob
        # coherence are strong.
        if green_dominance < 0.15:
            diseased_leaf_signature = (
                plant_like_ratio >= 0.40
                and largest_blob_ratio >= 0.50
            )
            held_leaf_signature = (
                plant_like_ratio >= 0.25
                and largest_blob_ratio >= 0.45
                and green_dominance >= 0.08
            )
            if not (diseased_leaf_signature or held_leaf_signature):
                raise ImageRejectedError(
                    code="non_leaf_or_non_plant_image",
                    message="This image does not contain enough green plant tissue. IRIS requires a clear rice leaf photo.",
                    metrics=metrics,
                    retry_guidance=[
                        "Upload a photo where the leaf is clearly visible with natural green coloring.",
                        "Diseased leaves still show some green - ensure the leaf is in the frame.",
                        "This does not appear to be a plant photo.",
                    ],
                )

        # Gate 4: scattered/fragmented plant pattern (lawns, grass-like shots)
        if (
            plant_like_ratio < 0.55
            and largest_blob_ratio < 0.22
            and blob_count >= 6
        ):
            raise ImageRejectedError(
                code="scattered_plant_pattern",
                message=(
                    "This image looks like scattered foliage (such as a lawn or distant grass) "
                    "rather than a close-up of a single leaf. IRIS needs one leaf clearly in frame."
                ),
                metrics=metrics,
                retry_guidance=[
                    "Move closer so a single rice leaf fills most of the frame.",
                    "Avoid wide shots of grass, lawns, or distant plants.",
                    "Ensure the leaf surface and any symptoms are clearly visible.",
                ],
            )

        return ImageGuardResult(width=width, height=height, metrics=metrics)

    @staticmethod
    def _entropy(luminance: np.ndarray) -> float:
        hist, _ = np.histogram(luminance, bins=64, range=(0.0, 1.0))
        total = hist.sum()
        if total == 0:
            return 0.0
        probabilities = hist[hist > 0] / total
        return float(-(probabilities * np.log2(probabilities)).sum())

    @staticmethod
    def _edge_density(luminance: np.ndarray) -> float:
        grad_x = np.abs(np.diff(luminance, axis=1))
        grad_y = np.abs(np.diff(luminance, axis=0))
        edge_pixels = int((grad_x > 0.06).sum() + (grad_y > 0.06).sum())
        possible_edges = grad_x.size + grad_y.size
        return edge_pixels / possible_edges if possible_edges else 0.0

    @staticmethod
    def _saturation(arr: np.ndarray) -> np.ndarray:
        max_channel = arr.max(axis=2)
        min_channel = arr.min(axis=2)
        return (max_channel - min_channel) / np.maximum(max_channel, 1e-6)

    @staticmethod
    def _plant_mask(
        red: np.ndarray,
        green: np.ndarray,
        blue: np.ndarray,
        luminance: np.ndarray,
        saturation: np.ndarray,
    ) -> np.ndarray:
        green_leaf = (green > red * 0.92) & (green > blue * 0.95) & (luminance > 0.12) & (saturation > 0.06)
        light_green = (green > red * 0.98) & (green > blue * 1.1) & (luminance > 0.3) & (saturation > 0.10)
        dark_green = (green > red * 0.90) & (green > blue * 0.90) & (luminance > 0.05) & (luminance < 0.35) & (saturation > 0.15)

        core_green = green_leaf | light_green | dark_green
        core_green_ratio = float(core_green.mean())

        # Brown/yellow only count as plant if the image already has significant green;
        # otherwise game art, food, and faces inflate the ratio.
        if core_green_ratio > 0.08:
            yellow_leaf = (red > 0.35) & (green > 0.30) & (blue < 0.28) & (saturation > 0.22) & (green > blue * 1.15)
            brown_leaf = (red > green * 1.0) & (green > blue * 1.15) & (red > 0.22) & (luminance > 0.12) & (saturation > 0.15)
            return core_green | yellow_leaf | brown_leaf
        return core_green

    @staticmethod
    def _connected_components(mask: np.ndarray, target_size: int = 32) -> tuple[float, int]:
        """Estimate (largest_blob_ratio, blob_count) using BFS on a downsampled mask."""
        if not mask.any():
            return 0.0, 0
        h, w = mask.shape
        step_h = max(1, h // target_size)
        step_w = max(1, w // target_size)
        small = mask[::step_h, ::step_w].astype(bool)
        sh, sw = small.shape
        visited = np.zeros_like(small, dtype=bool)
        sizes: list[int] = []
        for y0 in range(sh):
            for x0 in range(sw):
                if not small[y0, x0] or visited[y0, x0]:
                    continue
                stack = [(y0, x0)]
                size = 0
                while stack:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= sh or cx < 0 or cx >= sw:
                        continue
                    if visited[cy, cx] or not small[cy, cx]:
                        continue
                    visited[cy, cx] = True
                    size += 1
                    stack.append((cy + 1, cx))
                    stack.append((cy - 1, cx))
                    stack.append((cy, cx + 1))
                    stack.append((cy, cx - 1))
                sizes.append(size)
        total = int(small.sum())
        if total == 0 or not sizes:
            return 0.0, 0
        largest = max(sizes)
        significant = sum(1 for s in sizes if s >= 3)
        return float(largest) / float(total), significant

    @staticmethod
    def _green_dominance(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> float:
        """Fraction of pixels where green is the dominant channel."""
        green_dominant = (green > red) & (green > blue)
        return float(green_dominant.mean())

    @staticmethod
    def _color_diversity(arr: np.ndarray) -> float:
        """Measure color diversity via unique hue bins - natural leaf images have moderate diversity."""
        flat = arr.reshape(-1, 3)
        quantized = (flat * 8).astype(int).clip(0, 7)
        unique_bins = len(set(map(tuple, quantized)))
        return unique_bins / 512.0


def confidence_is_suspicious(
    confidence: float,
    plant_like_ratio: float,
    entropy: float,
    green_dominance: float = 1.0,
    largest_blob_ratio: float = 1.0,
) -> bool:
    """Check if a model prediction is likely an OOD false positive.

    IRIS adaptation vs PhyToSignal: the hard green-dominance veto now carries
    the same coherent-diseased-leaf exception used by the guard's Gate 3  - 
    heavily necrotic leaves lose *global* green dominance (lesions take over
    the frame) while remaining strongly plant-like in one coherent region.
    Without this, a blast lesion at 99%+ confidence would be rejected as OOD.
    """
    # Only trust high confidence when green dominance is solid...
    if green_dominance < 0.20:
        # ...unless the image shows a single coherent, strongly plant-like
        # region WITH natural-lighting texture evidence. This mirrors the
        # diseased_leaf_signature of Gate 3 plus an entropy floor: necrotic
        # lesions crush *global* green dominance while leaving rich
        # vein/lesion texture (entropy >= 3.0 on real photos), whereas flat
        # warm scenes that merely contain some green (potted plant on a
        # deck, turf over bare soil) sit well below it and must stay
        # OOD-suspect. Threshold tuned so all bundled leaf samples pass
        # (measured entropy ~5.20) and synthetic flat scenes fail (~1.9-2.4).
        coherent_diseased_leaf = (
            plant_like_ratio >= 0.40
            and largest_blob_ratio >= 0.50
            and entropy >= 3.0
        )
        if not coherent_diseased_leaf:
            return True
    if plant_like_ratio >= 0.55 and green_dominance >= 0.30:
        return False
    if confidence < 0.50:
        return True
    if confidence < 0.65 and plant_like_ratio < 0.30:
        return True
    if confidence < 0.80 and plant_like_ratio < 0.20:
        return True
    if entropy > 5.5 and plant_like_ratio < 0.25:
        return True
    return False
