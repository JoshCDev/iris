import time

import pytest

from app.vision.advisory import AdvisoryService
from app.vision.crop_packs import RICE_SLUG, CropPackService
from app.vision.image_guard import ImageGuardService
from app.vision.inference import (InferenceCandidate, InferenceResult,
                                  InferenceService)
from app.vision.severity import calculate_severity, severity_label

MODEL_CLASSES = {
    "bacterial_leaf_blight", "blast", "brown_spot", "healthy", "tungro",
}
FIXTURE = __file__.replace("\\", "/").rsplit("/", 1)[0] + "/fixtures/rice_leaf.jpg"


@pytest.fixture(scope="module")
def vision():
    packs = CropPackService()
    packs.load()
    svc = InferenceService(packs)
    svc.load()
    return packs, svc, ImageGuardService(), AdvisoryService(packs)


def test_real_onnx_triage_on_fixture(vision):
    packs, svc, guard, _ = vision
    image_bytes = open(FIXTURE, "rb").read()
    quality = guard.analyze(image_bytes)
    t0 = time.perf_counter()
    result = svc.predict(RICE_SLUG, image_bytes,
                         quality_metrics=quality.metrics)
    elapsed = time.perf_counter() - t0
    predicted = result.predicted
    assert predicted.class_slug in MODEL_CLASSES
    assert 0.0 < predicted.confidence <= 1.0
    assert len(result.top3) == 3
    assert elapsed < 3.0


def test_pack_metadata_and_model_classes(vision):
    packs, _, _, _ = vision
    pack = packs.get(RICE_SLUG)
    assert pack["status"] == "active"
    assert set(pack["model_classes"]) == MODEL_CLASSES
    assert packs.model_path(RICE_SLUG).exists()
    meta = packs.metadata(RICE_SLUG)
    assert meta["input_size"] == [224, 224]
    assert meta["normalization"] == "imagenet"


def test_advisory_bilingual_summaries(vision):
    _, _, _, advisory = vision
    for lang in ("id", "en"):
        entry = advisory.build(RICE_SLUG, "brown_spot", lang)
        assert entry["language"] == lang
        assert entry["summary"]
        assert "triage" in entry["disclaimer"]
        assert entry["immediate_steps"]


def test_severity_scale_and_labels():
    assert severity_label(10) == "Low"
    assert severity_label(40) == "Moderate"
    assert severity_label(70) == "High"
    assert severity_label(95) == "Urgent Review"
    score, label, needs_review = calculate_severity(
        class_slug="brown_spot", confidence=0.9, risk_weight=0.55,
        recent_same_area_count=0, default_expert_review=False)
    assert score == round(0.9 * 50 + 0.55 * 35)
    assert label == severity_label(score)
    assert needs_review is True


def test_healthy_synthesis_for_uncertain_clean_leaf(vision):
    _, svc, _, _ = vision
    original = InferenceResult(
        top3=[InferenceCandidate("brown_spot", 0.31),
              InferenceCandidate("blast", 0.30),
              InferenceCandidate("tungro", 0.29)],
        model_version="test", runtime="test")
    synthesized = svc._healthy_result(original)
    assert synthesized.predicted.class_slug == "healthy"
    assert synthesized.predicted.confidence == pytest.approx(0.69)
