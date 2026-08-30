import pytest
from fastapi.testclient import TestClient

from app import db
from app import main as main_mod
from app.db_l1 import latest_recommendation

PINNED_TODAY_KEYS = {"plot", "freshness", "water", "weather",
                     "recommendation", "latest_leaf"}


def _client(tmp_path, monkeypatch, rain=6.5):
    db.init_db(f"sqlite:///{(tmp_path / 'v1.db').as_posix()}")
    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain",
        lambda **kw: rain)
    return TestClient(main_mod.app)


def test_post_observation_creates_recommendation(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, rain=6.5)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak Utara",
                             transplant_date="2026-07-01", is_demo=False)
    r = c.post(f"/api/v1/plots/{pid}/water-observations",
               json={"level_cm": -15.2, "source": "manual"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == PINNED_TODAY_KEYS
    assert body["plot"]["name"] == "Petak Utara"
    assert body["water"]["level_cm"] == -15.2
    assert body["weather"]["availability"] == "fresh"
    assert body["recommendation"]["action"] == "IRRIGATE"
    assert body["recommendation"]["confirmation_state"] == "pending"
    with db.session_scope() as conn:
        rec = latest_recommendation(conn, pid)
        assert rec is not None and rec["action"] == "IRRIGATE"


def test_today_no_observation_has_null_recommendation(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Kosong",
                             transplant_date="2026-07-01", is_demo=False)
    body = c.get(f"/api/v1/plots/{pid}/today").json()
    assert set(body.keys()) == PINNED_TODAY_KEYS
    assert body["recommendation"] is None
    assert body["water"]["level_cm"] is None


def test_post_rejects_implausible_level(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    r = c.post(f"/api/v1/plots/{pid}/water-observations",
               json={"level_cm": 999.0, "source": "manual"})
    assert r.status_code == 422
    assert r.json()["code"] == "implausible_level"


def test_unavailable_weather_forces_recheck(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)

    def boom(**kw):
        raise RuntimeError("BMKG offline")

    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain", boom)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    r = c.post(f"/api/v1/plots/{pid}/water-observations",
               json={"level_cm": -5.0, "source": "manual"})
    body = r.json()
    assert body["weather"]["availability"] == "unavailable"
    assert body["weather"]["rain72_mm"] is None
    assert body["recommendation"]["action"] == "RECHECK_REQUIRED"


def test_water_history_paginates(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, rain=6.5)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    for level in (-15.2, -8.0, -5.0):
        c.post(f"/api/v1/plots/{pid}/water-observations",
               json={"level_cm": level, "source": "manual"})
    body = c.get(f"/api/v1/plots/{pid}/water-history?limit=2").json()
    assert body["total"] == 3
    assert len(body["observations"]) == 2
    assert len(body["recommendations"]) == 2
    assert body["observations"][0]["level_cm"] == -5.0  # newest first


def test_confirmation_state_follows_latest_confirmation_status(tmp_path, monkeypatch):
    """A defer/decline must not read as "confirmed" (final review Finding 1)."""
    c = _client(tmp_path, monkeypatch, rain=6.5)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    body = c.post(f"/api/v1/plots/{pid}/water-observations",
                  json={"level_cm": -15.2, "source": "manual"}).json()
    rec_id = body["recommendation"]["id"]
    assert body["recommendation"]["confirmation_state"] == "pending"

    # Deferring the action must NOT mark the recommendation confirmed.
    r = c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
               json={"status": "deferred", "note": "wait for rain"})
    assert r.status_code == 200
    body = c.get(f"/api/v1/plots/{pid}/today").json()
    assert body["recommendation"]["confirmation_state"] == "pending"

    # Performing the action is the only state that confirms the record.
    r = c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
               json={"status": "performed", "volume_m3": 12.5})
    assert r.status_code == 200
    body = c.get(f"/api/v1/plots/{pid}/today").json()
    assert body["recommendation"]["confirmation_state"] == "confirmed"


def test_today_and_history_carry_data_kind(tmp_path, monkeypatch):
    """§11.2: the payload distinguishes manual/sensor/simulation by kind."""
    c = _client(tmp_path, monkeypatch, rain=6.5)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    body = c.post(f"/api/v1/plots/{pid}/water-observations",
                  json={"level_cm": -15.2, "source": "manual"}).json()
    assert body["water"]["source"] == "manual"
    assert body["water"]["kind"] == "manual"

    body = c.post(f"/api/v1/plots/{pid}/water-observations",
                  json={"level_cm": -8.0, "source": "demo"}).json()
    assert body["water"]["source"] == "demo"
    assert body["water"]["kind"] == "simulation"

    hist = c.get(f"/api/v1/plots/{pid}/water-history").json()
    kinds = {o["kind"] for o in hist["observations"]}
    assert kinds == {"manual", "simulation"}
    assert all("kind" in o for o in hist["observations"])


def test_today_no_observation_has_kind_other(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Kosong",
                             transplant_date="2026-07-01", is_demo=False)
    body = c.get(f"/api/v1/plots/{pid}/today").json()
    assert body["water"]["level_cm"] is None
    assert body["water"]["kind"] == "other"
