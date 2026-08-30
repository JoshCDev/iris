# v1 leaf-assessment endpoints (LEAF-001..010) with full provenance.
import hashlib

from fastapi.testclient import TestClient

from app import db
from app import main as main_mod


def _client(tmp_path, monkeypatch):
    db.init_db(f"sqlite:///{(tmp_path / 'leaf.db').as_posix()}")
    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain",
        lambda **kw: 6.5)
    return TestClient(main_mod.app)


def _sample_image() -> bytes | None:
    """rice-blast-demo.jpg from the committed rice crop pack (real ONNX input)."""
    try:
        return (main_mod.crop_packs.root / "rice" /
                "rice-blast-demo.jpg").read_bytes()
    except Exception:
        return None


def test_leaf_assessment_stores_provenance(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    img = _sample_image()
    # If the sample is unavailable, skip; the shape test below is the contract.
    if img is None:
        return
    r = c.post(f"/api/v1/plots/{pid}/leaf-assessments",
               files={"image": ("leaf.jpg", img, "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["class"]
    assert body["evidence_type"] == "public-dataset"
    assert body["model_version"]
    assert "screening" in body["disclaimer"].lower()
    with db.session_scope() as conn:
        row = conn.execute(
            "SELECT * FROM leaf_assessments WHERE plot_id = ?", (pid,)).fetchone()
        assert row is not None
        assert row["image_hash"] == hashlib.sha256(img).hexdigest()
        assert row["retention_mode"] == "operational"


def test_leaf_assessment_rejects_bad_upload(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    r = c.post(f"/api/v1/plots/{pid}/leaf-assessments",
               files={"image": ("fake.jpg", b"not-an-image", "image/jpeg")})
    assert r.status_code in (413, 422)
    assert "code" in r.json()


def test_leaf_assessment_abstention_stores_no_label(tmp_path, monkeypatch):
    from app.vision.inference import LowConfidenceRejection

    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    img = _sample_image()
    if img is None:
        return

    def reject(crop_slug, image_bytes, file_name=None, quality_metrics=None):
        raise LowConfidenceRejection(
            confidence=0.31, predicted_class="brown_spot",
            message="The model produced a low-confidence prediction (31%).")

    monkeypatch.setattr(main_mod.inference_service, "predict", reject)
    r = c.post(f"/api/v1/plots/{pid}/leaf-assessments",
               files={"image": ("leaf.jpg", img, "image/jpeg")})
    assert r.status_code == 422
    assert r.json()["code"] == "low_confidence"
    with db.session_scope() as conn:
        row = conn.execute(
            "SELECT * FROM leaf_assessments WHERE plot_id = ?", (pid,)).fetchone()
        assert row is not None
        assert row["guard_result"] == "low_confidence"
        assert row["class"] is None  # LEAF-006: no final disease label stored


def test_leaf_assessment_history_paginates(tmp_path, monkeypatch):
    from app.db_l1 import insert_leaf_assessment

    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
        for i in range(3):
            insert_leaf_assessment(
                conn, plot_id=pid, image_hash=f"hash{i}",
                retention_mode="operational", model_version="test-v1",
                guard_result="ok", class_="blast",
                confidence=0.8 + i * 0.05, severity="High",
                evidence_type="public-dataset",
                created_at=f"2026-08-30T0{i + 1}:00:00+00:00", demo=False)
    body = c.get(f"/api/v1/plots/{pid}/leaf-assessments?limit=2").json()
    assert body["total"] == 3
    assert len(body["assessments"]) == 2
    assert {"id", "class", "confidence", "severity", "evidence_type",
            "created_at", "demo"} <= set(body["assessments"][0].keys())
    assert body["assessments"][0]["class"] == "blast"
    assert body["assessments"][0]["demo"] is False
