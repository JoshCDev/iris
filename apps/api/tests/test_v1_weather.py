from fastapi.testclient import TestClient

from app import db
from app import main as main_mod


def _client(tmp_path, monkeypatch, rain=6.5):
    db.init_db(f"sqlite:///{(tmp_path / 'w.db').as_posix()}")
    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain",
        lambda **kw: rain)
    return TestClient(main_mod.app)


def test_v1_weather_has_availability_and_hitl(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, rain=6.5)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    c.post(f"/api/v1/plots/{pid}/water-observations",
           json={"level_cm": -5.0, "source": "manual"})
    body = c.get(f"/api/v1/plots/{pid}/weather").json()
    assert body["availability"] == "fresh"
    assert body["rain72_mm"] == 6.5
    assert "secondary_review" in body


def test_v1_weather_unavailable_never_zero(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)

    def boom(**kw):
        raise RuntimeError("offline")

    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain", boom)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    c.post(f"/api/v1/plots/{pid}/water-observations",
           json={"level_cm": -5.0, "source": "manual"})
    body = c.get(f"/api/v1/plots/{pid}/weather").json()
    assert body["availability"] == "unavailable"
    assert body["rain72_mm"] is None
