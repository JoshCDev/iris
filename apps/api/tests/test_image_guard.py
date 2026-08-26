import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.vision.image_guard import (ImageGuardService, ImageRejectedError,
                                    confidence_is_suspicious)

GUARD = ImageGuardService()
FIXTURE = __file__.replace("\\", "/").rsplit("/", 1)[0] + "/fixtures/rice_leaf.jpg"
TESTS_DIR = Path(__file__).resolve().parent
RICE_PACK = TESTS_DIR.parent / "crop_packs" / "rice"
BUNDLED_LEAF_SAMPLES = [
    TESTS_DIR / "fixtures" / "rice_leaf.jpg",
    RICE_PACK / "rice-blast-demo.jpg",
    RICE_PACK / "rice-blast-demo.webp",
]


def _jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _solid(color: tuple[int, int, int], size=(300, 300)) -> bytes:
    return _jpeg(Image.new("RGB", size, color))


def test_rejects_solid_green_image():
    with pytest.raises(ImageRejectedError) as exc:
        GUARD.analyze(_solid((40, 120, 40)))
    assert exc.value.code == "blank_or_solid_image"


def test_rejects_solid_white_and_black():
    for color in ((255, 255, 255), (0, 0, 0)):
        with pytest.raises(ImageRejectedError) as exc:
            GUARD.analyze(_solid(color))
        assert exc.value.code == "blank_or_solid_image"
        assert exc.value.metrics["luminance_std"] < 0.018


def test_rejects_unreadable_bytes():
    with pytest.raises(ImageRejectedError) as exc:
        GUARD.analyze(b"this is definitely not an image")
    assert exc.value.code == "unreadable_image"


def test_rejects_too_small_image():
    with pytest.raises(ImageRejectedError) as exc:
        GUARD.analyze(_solid((10, 200, 10), size=(60, 60)))
    assert exc.value.code == "image_too_small"


def test_accepts_real_rice_leaf_fixture():
    result = GUARD.analyze(open(FIXTURE, "rb").read())
    assert result.width >= 80 and result.height >= 80
    assert result.metrics["plant_like_ratio"] > 0.08
    assert "entropy" in result.metrics


def test_noise_image_is_rejected_as_non_leaf():
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 256, size=(300, 300, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(noise.astype(np.uint8)).save(buf, format="PNG")
    with pytest.raises(ImageRejectedError):
        GUARD.analyze(buf.getvalue())


# --- OOD confidence gating ---------------------------------------------------

def test_confident_coherent_diseased_leaf_not_suspicious_despite_low_green():
    # blast demo profile: green_dominance ~0.14 but one coherent blob
    assert confidence_is_suspicious(
        confidence=0.9996, plant_like_ratio=0.44, entropy=5.2,
        green_dominance=0.137, largest_blob_ratio=0.83) is False


def test_low_green_without_coherent_blob_still_suspicious():
    assert confidence_is_suspicious(
        confidence=0.99, plant_like_ratio=0.30, entropy=5.2,
        green_dominance=0.10, largest_blob_ratio=0.15) is True


def test_uncertain_predictions_flagged():
    # green 0.25 sits below the early-pass band (plant>=0.55 AND green>=0.30),
    # so the low-confidence check must fire.
    assert confidence_is_suspicious(
        confidence=0.45, plant_like_ratio=0.60, entropy=1.0,
        green_dominance=0.25) is True


# --- non-leaf regression: coherent warm blobs without leaf texture -----------

def test_flat_warm_scene_with_green_patch_is_ood_suspect():
    # Potted-plant-on-deck profile measured from a synthetic probe: one huge
    # warm "plant-like" blob (brown/yellow pixels counted once a little green
    # unlocks the wide mask), green dominance far below the 0.20 trust bar,
    # and flat photographic texture (luminance entropy < 3.0). The original
    # PhyToSignal veto rejected this class outright; the carve-out must not
    # resurrect it.
    assert confidence_is_suspicious(
        confidence=0.95, plant_like_ratio=1.0, entropy=2.39,
        green_dominance=0.0865, largest_blob_ratio=1.0) is True


def test_low_green_coherent_blob_requires_texture_evidence():
    # The diseased/held-leaf carve-out additionally requires luminance
    # entropy >= 3.0 (natural-lighting texture). Boundary tolerance: probes
    # are asserted at least 0.2 from the 3.0 threshold; values within
    # +/-0.2 of it are treated as ambiguous by design.
    flat = dict(confidence=0.99, plant_like_ratio=1.0,
                green_dominance=0.10, largest_blob_ratio=1.0)
    textured = dict(confidence=0.9996, plant_like_ratio=0.44,
                    green_dominance=0.137, largest_blob_ratio=0.83)
    assert confidence_is_suspicious(entropy=2.8, **flat) is True
    assert confidence_is_suspicious(entropy=5.2, **textured) is False


def test_all_bundled_leaf_samples_pass_guard_and_confidence_gate():
    assert len(BUNDLED_LEAF_SAMPLES) == 3
    for path in BUNDLED_LEAF_SAMPLES:
        result = GUARD.analyze(path.read_bytes())
        m = result.metrics
        # Heavily lesioned demo leaves lose global green dominance; the
        # carve-out must keep admitting them end-to-end.
        assert confidence_is_suspicious(
            confidence=0.9996, plant_like_ratio=m["plant_like_ratio"],
            entropy=m["entropy"], green_dominance=m["green_dominance"],
            largest_blob_ratio=m["largest_blob_ratio"]) is False, path.name


def _turf_over_soil_bytes() -> bytes:
    """Thin green blades scattered over dark soil: reads as one huge warm
    'plant' blob with low global green dominance and flat texture, yet the
    bundled ONNX model confidently calls it blast (measured ~0.89). Exactly
    the class of photo the owner complained about."""
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (86, 64, 46))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(31)
    for _ in range(2400):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        g = int(rng.integers(95, 185))
        rr = max(20, g // 2 - int(rng.integers(0, 12)))
        d.line((x, y, x + int(rng.integers(-9, 10)), y - int(rng.integers(10, 26))),
               fill=(rr, g, max(8, rr - 16)), width=1)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def test_turf_scene_confidently_misclassified_is_rejected_end_to_end():
    pytest.importorskip("onnxruntime")
    from app.vision.crop_packs import RICE_SLUG, CropPackService
    from app.vision.inference import InferenceService, LowConfidenceRejection

    packs = CropPackService(RICE_PACK.parent)
    packs.load()
    svc = InferenceService(packs)
    svc.load()
    if not svc.onnx.is_loaded(RICE_SLUG):
        pytest.skip("rice ONNX model not bundled")

    data = _turf_over_soil_bytes()
    quality = GUARD.analyze(data)  # deliberately passes Stage 1
    # Precondition for this regression test: the model must be CONFIDENT on
    # this non-leaf scene (closed-set softmax always picks one of 4 classes);
    # otherwise the generic low-confidence path would mask the bug.
    top = svc.onnx.predict(RICE_SLUG, data).predicted
    assert top.confidence >= 0.80, f"fixture no longer adversarial: {top}"
    with pytest.raises(LowConfidenceRejection):
        svc.predict(RICE_SLUG, data, file_name="turf.jpg",
                    quality_metrics=quality.metrics)
