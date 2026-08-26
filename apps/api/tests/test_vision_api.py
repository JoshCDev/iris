import io
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import db
from app.vision.crop_packs import RICE_SLUG
from app.vision.inference import InferenceCandidate, InferenceResult, \
    LowConfidenceRejection
import app.main as main_mod

PINNED_VISION_KEYS = {"report_id", "top_class", "class_label_id",
                      "class_label_en", "confidence", "severity",
                      "advisory_id", "advisory_en", "fusion", "is_demo"}
MODEL_CLASSES = {"blast", "brown_spot", "tungro", "bacterial_leaf_blight"}
FIXTURE = __file__.replace("\\", "/").rsplit("/", 1)[0] + "/fixtures/rice_leaf.jpg"


def _solid_green_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), (40, 120, 40)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    db.init_db(f"sqlite:///{(tmp_path / 'vision.db').as_posix()}")
    monkeypatch.setattr(main_mod, "fetch_forecast_72h_rain",
                        lambda a, b: 0.0)
    main_mod._weather_cache["ts"] = 0.0
    main_mod._weather_cache["value"] = None
    return TestClient(main_mod.app)


def _stub_result(class_slug: str = "brown_spot",
                 confidence: float = 0.9) -> InferenceResult:
    others = [c for c in ("blast", "tungro", "bacterial_leaf_blight")
              if c != class_slug]
    return InferenceResult(
        top3=[InferenceCandidate(class_slug, confidence),
              InferenceCandidate(others[0], round((1 - confidence) * 0.6, 3)),
              InferenceCandidate(others[1], round((1 - confidence) * 0.3, 3))],
        model_version="stub", runtime="stub")


def _demo_plot_deep_dry() -> int:
    """Plot in veg_awd stage with latest decision at -12 cm (deep_dry band)."""
    transplant = (date.today() - timedelta(days=30)).isoformat()
    ts = datetime.now(timezone.utc).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Sawah Fusion", variety="Ciherang",
                             transplant_date=transplant)
        db.insert_reading(conn, plot_id=pid, ts=ts, dist_cm=42.0,
                          level_cm=-12.0, batt_v=3.95)
        db.insert_decision(conn, plot_id=pid, ts=ts, stage="veg_awd",
                           level_cm=-12.0, action="WAIT",
                           reason_id="within_band", rain72_mm=0.0)
    return pid


# --- happy path: real model through the API ---------------------------------

def test_predict_returns_pinned_shape_with_real_model(client):
    with open(FIXTURE, "rb") as fh:
        r = client.post("/api/vision/predict",
                        files={"image": ("rice_leaf.jpg", fh, "image/jpeg")},
                        data={"language": "en"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == PINNED_VISION_KEYS
    assert body["top_class"] in MODEL_CLASSES
    assert 0.0 < body["confidence"] <= 1.0
    assert body["class_label_id"] and body["class_label_en"]
    assert body["severity"]
    assert body["advisory_id"] and body["advisory_en"]
    assert body["fusion"] is None
    assert body["is_demo"] is False


def test_predict_defaults_to_english_and_persists_report(client):
    with open(FIXTURE, "rb") as fh:
        r = client.post("/api/vision/predict",
                        files={"image": ("rice_leaf.jpg", fh, "image/jpeg")})
    body = r.json()
    assert set(body.keys()) == PINNED_VISION_KEYS
    with db.session_scope() as conn:
        row = conn.execute(
            "SELECT * FROM vision_reports WHERE id = ?",
            (body["report_id"],)).fetchone()
    assert row is not None
    assert row["language"] == "en"
    assert row["plot_id"] is None
    assert row["is_demo"] == 0
    advisory = json.loads(row["advisory_json"])
    assert set(advisory.keys()) == {"id", "en"}


def test_vision_reports_lists_recent(client):
    with open(FIXTURE, "rb") as fh:
        client.post("/api/vision/predict",
                    files={"image": ("rice_leaf.jpg", fh, "image/jpeg")})
    r = client.get("/api/vision/reports")
    assert r.status_code == 200
    reports = r.json()["reports"]
    assert 1 <= len(reports) <= 20
    assert {"report_id", "ts", "top_class", "confidence", "is_demo"} <= \
        set(reports[0].keys())


# --- honest rejection paths ---------------------------------------------------

def test_solid_image_rejected_422_image_rejected(client):
    r = client.post("/api/vision/predict",
                    files={"image": ("solid.png", _solid_green_jpeg(),
                                     "image/png")})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "image_rejected"
    assert body["detail"]


def test_low_confidence_stubbed_rejection(client, monkeypatch):
    def reject(crop_slug, image_bytes, **kwargs):
        raise LowConfidenceRejection(
            confidence=0.31, predicted_class="brown_spot",
            message="The model produced a low-confidence prediction "
                    "(31% for brown_spot). This image may not contain a "
                    "recognizable rice leaf.")
    monkeypatch.setattr(main_mod.inference_service, "predict", reject)
    r = client.post("/api/vision/predict",
                    files={"image": ("rice_leaf.jpg", open(FIXTURE, "rb"),
                                     "image/jpeg")})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "low_confidence"
    assert "31%" in body["detail"]


# --- fusion integration -------------------------------------------------------

def test_fusion_deep_dry_brown_spot_high_with_irrigation_note(
        client, monkeypatch):
    plot_id = _demo_plot_deep_dry()
    monkeypatch.setattr(main_mod.inference_service, "predict",
                        lambda *a, **k: _stub_result("brown_spot", 0.90))
    with open(FIXTURE, "rb") as fh:
        r = client.post("/api/vision/predict",
                        files={"image": ("rice_leaf.jpg", fh, "image/jpeg")},
                        data={"plot_id": str(plot_id)})
    assert r.status_code == 200
    body = r.json()
    fusion = body["fusion"]
    assert fusion is not None
    assert fusion["risk_level"] == "high"
    assert fusion["drivers_id"] == ["Cekaman air memicu bercak cokelat"]
    assert fusion["irrigation_note"] == "consider a shorter AWD cycle"
    assert isinstance(fusion["drivers_en"], list) and fusion["drivers_en"]
    with db.session_scope() as conn:
        row = conn.execute(
            "SELECT fusion_json FROM vision_reports WHERE id = ?",
            (body["report_id"],)).fetchone()
    assert row["fusion_json"] is not None


def test_fusion_unknown_plot_404(client):
    with open(FIXTURE, "rb") as fh:
        r = client.post("/api/vision/predict",
                        files={"image": ("rice_leaf.jpg", fh, "image/jpeg")},
                        data={"plot_id": "999"})
    assert r.status_code == 404


def test_flooded_healthy_maps_to_none_low(client, monkeypatch):
    transplant = (date.today() - timedelta(days=5)).isoformat()
    ts = datetime.now(timezone.utc).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Sawah Basah",
                             transplant_date=transplant)
        db.insert_reading(conn, plot_id=pid, ts=ts, dist_cm=28.0,
                          level_cm=2.0, batt_v=4.0)
        db.insert_decision(conn, plot_id=pid, ts=ts, stage="establishment",
                           level_cm=2.0, action="WAIT",
                           reason_id="flooded", rain72_mm=0.0)
    monkeypatch.setattr(main_mod.inference_service, "predict",
                        lambda *a, **k: _stub_result("healthy", 0.7))
    with open(FIXTURE, "rb") as fh:
        r = client.post("/api/vision/predict",
                        files={"image": ("rice_leaf.jpg", fh, "image/jpeg")},
                        data={"plot_id": str(pid)})
    body = r.json()
    assert body["fusion"]["risk_level"] == "low"
    assert body["top_class"] == "healthy"


# --- real-model smoke (spec §9) ----------------------------------------------

def test_real_model_smoke_fixture_class_in_four_diseases(client):
    with open(FIXTURE, "rb") as fh:
        r = client.post("/api/vision/predict",
                        files={"image": ("rice_leaf.jpg", fh, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["top_class"] in MODEL_CLASSES


def test_health_reports_onnx_loaded(client, monkeypatch):
    from app.assistant import agent

    agent.reset_llm_probe_cache()
    monkeypatch.setattr(agent, "llm_status", lambda force=False: "unreachable")
    body = client.get("/api/health").json()
    assert body["onnx"] == "loaded"
    # pinned contract: llm/mode are live-probed values, never scaffold strings
    assert body["llm"] in {"reachable", "unreachable"}
    assert body["mode"] in {"live", "offline"}
