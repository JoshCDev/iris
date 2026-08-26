"""Tool handler tests - all against a seeded tmp db, no network."""
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

from app import db
from app.assistant import tools


def _seed_plot(name="Sawah Uji", level=-12.0, action="WAIT",
               rain72=0.0, stage="veg_awd"):
    now = datetime.now(timezone.utc).isoformat()
    transplant = (date.today() - timedelta(days=30)).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name=name,
                             transplant_date=transplant, lat=-7.3305,
                             lon=110.5064)
        db.insert_reading(conn, plot_id=pid, ts=now, dist_cm=42.0,
                          level_cm=level, batt_v=3.95)
        db.insert_decision(conn, plot_id=pid, ts=now, stage=stage,
                           level_cm=level, action=action,
                           reason_id="uji", rain72_mm=rain72)
    return pid


@pytest.fixture
def seeded_db(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'tools.db').as_posix()}")
    return _seed_plot()


# --- get_plot_status ---------------------------------------------------------

def test_get_plot_status_returns_pinned_keys(seeded_db):
    out = tools.get_plot_status()
    assert "error" not in out
    for key in ("plot_id", "name", "level_cm", "stage", "stage_days",
                "action", "reason_id", "rain72_mm", "next_check",
                "last_ts", "is_demo"):
        assert key in out
    assert out["plot_id"] == seeded_db
    assert out["level_cm"] == -12.0
    assert out["action"] == "WAIT"


def test_get_plot_status_by_explicit_id(seeded_db):
    out = tools.get_plot_status(plot_id=seeded_db)
    assert out["name"] == "Sawah Uji"


def test_get_plot_status_unknown_plot(seeded_db):
    assert "error" in tools.get_plot_status(plot_id=424242)


def test_get_plot_status_no_plots(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    assert tools.get_plot_status() == {"error": "no plots registered yet"}


# --- get_weather -------------------------------------------------------------

def test_get_weather_ok(monkeypatch, seeded_db):
    from app.irrigation import weather_bmkg as w

    monkeypatch.setattr(w, "fetch_forecast_72h_rain", lambda *a, **k: 17.5)
    out = tools.get_weather()
    assert out == {"rain72_mm": 17.5, "stale": False}


def test_get_weather_fail_open(monkeypatch, seeded_db):
    from app.irrigation import weather_bmkg as w

    def boom(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(w, "fetch_forecast_72h_rain", boom)
    out = tools.get_weather()
    assert out == {"rain72_mm": 0.0, "stale": True}


# --- search_kb ---------------------------------------------------------------

def test_search_kb_cites_file(seeded_db):
    out = tools.search_kb("apa itu safe awd dan kapan sawah diairi?")
    assert out["confident"] is True
    assert "AWD" in out["answer"]
    assert "[Source:" not in out["answer"]
    assert out["citations"] == ["awd-dasar.md"]


def test_search_kb_honest_miss(seeded_db):
    out = tools.search_kb("resep rendang padang asli")
    assert out["confident"] is False
    assert "outside the IRIS knowledge base" in out["answer"]


# --- get_receipt / get_risk_fusion --------------------------------------------

def test_get_receipt_unknown_plot(seeded_db):
    out = tools.get_receipt(999)
    assert "error" in out


def test_get_receipt_e3_on_empty_plot(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Kosong",
                             transplant_date=date.today().isoformat())
    out = tools.get_receipt(pid)
    assert "error" not in out
    assert out["claim_source"] == "e3_backtest"
    assert out["water_saved_pct"] == 37.5
    assert out["flooded_days"] == 51


def test_get_risk_fusion_brown_spot_deep_dry_high(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'f.db').as_posix()}")
    pid = _seed_plot(level=-12.0, action="IRRIGATE")
    with db.session_scope() as conn:
        conn.execute(
            "INSERT INTO vision_reports (plot_id, ts, image_path, top_class,"
            " confidence, severity, language, advisory_json, fusion_json,"
            " is_demo) VALUES (?, ?, 'x.jpg', 'brown_spot', 0.9, 'moderate',"
            " 'id', '{}', NULL, 0)",
            (pid, datetime.now(timezone.utc).isoformat()))
    out = tools.get_risk_fusion(pid)
    assert out["risk_level"] == "high"
    assert out["disease"] == "brown_spot"
    assert out["awd_state"] == "deep_dry"
    assert "irrigation_note" in out
    assert out["drivers_id"]


def test_get_risk_fusion_unknown_plot(seeded_db):
    assert "error" in tools.get_risk_fusion(999)


# --- run_vision_triage ----------------------------------------------------------

def test_vision_tool_unknown_ref(seeded_db):
    out = tools.run_vision_triage("img_does_not_exist")
    assert out == {"error": "unknown or expired image_ref"}


def test_vision_tool_graceful_when_module_missing(seeded_db, monkeypatch):
    ref = tools.register_image_ref(b"\x89PNG-fake-bytes")

    def _raise():
        raise ImportError("app.vision not installed")

    monkeypatch.setattr(tools, "_vision_stack", _raise)
    out = tools.run_vision_triage(ref)
    assert out == {"error": "vision is not ready"}


def test_vision_tool_ready_path_mocked(seeded_db, monkeypatch):
    ref = tools.register_image_ref(b"\x89PNG-fake-bytes")

    class _Quality:
        metrics = {"entropy": 2.0}

    class _Predicted:
        class_slug = "brown_spot"
        confidence = 0.91

    class _Result:
        predicted = _Predicted()

    class _Guard:
        @staticmethod
        def analyze(data):
            return _Quality()

    class _Inference:
        @staticmethod
        def predict(slug, data, file_name=None, quality_metrics=None):
            return _Result()

    class _Packs:
        @staticmethod
        def get_class_by_slug(slug, cls):
            return {"name_id": "Bercak Cokelat", "name_en": "Brown Spot",
                    "risk_weight": 1}

        @staticmethod
        def risk_rule_for(slug, cls):
            return {}

    class _Advisory:
        @staticmethod
        def build_bilingual(slug, cls):
            return {"id": {"summary": "advisory id"},
                    "en": {"summary": "advisory en"}}

    monkeypatch.setattr(tools, "_vision_stack", lambda: (
        "rice", (lambda: True), _Advisory(), _Packs(), _Guard(),
        _Inference(), type("IRE", (Exception,), {}),
        type("LCE", (Exception,), {}),
        lambda **kw: (0, "Low", False),
    ))
    out = tools.run_vision_triage(ref)
    assert out["top_class"] == "brown_spot"
    assert out["class_label_id"] == "Bercak Cokelat"
    assert out["severity"] == "Low"
    assert out["note"] == "screening, not a diagnosis"


# --- image-ref registry TTL -----------------------------------------------------

def test_register_image_ref_ttl_expiry(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(tools, "_now", lambda: clock["t"])
    ref = tools.register_image_ref(b"abc")
    assert tools.get_image_ref(ref) == b"abc"
    clock["t"] += tools._IMAGE_TTL_S + 1.0
    assert tools.get_image_ref(ref) is None


def test_register_image_dataref_passthrough_and_decode(monkeypatch):
    import base64

    clock = {"t": 0.0}
    monkeypatch.setattr(tools, "_now", lambda: clock["t"])
    ref = tools.register_image_ref(b"hello")
    assert tools.register_image_dataref(ref) == ref
    b64 = base64.b64encode(b"world").decode()
    ref2 = tools.register_image_dataref("data:image/jpeg;base64," + b64)
    assert tools.get_image_ref(ref2) == b"world"
    with pytest.raises(ValueError):
        tools.register_image_dataref("!!!not-b64!!!")


def test_dispatch_reports_latency_and_unknown(seeded_db):
    out, ms = tools.dispatch("get_weather", {})
    assert ms >= 0.0
    assert "rain72_mm" in out
    out2, _ = tools.dispatch("no_such_tool", {})
    assert "error" in out2


def test_args_summary_truncates():
    long_args = {"q": "x" * 500}
    assert len(tools.args_summary(long_args)) <= 120
