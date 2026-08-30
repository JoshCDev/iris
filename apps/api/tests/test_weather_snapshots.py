from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.weather.snapshots import (
    capture_weather_snapshot,
    latest_weather_snapshot,
    weather_state_payload,
)


def _plot(conn) -> int:
    return db.create_plot(conn, name="Petak", transplant_date="2026-01-01")


def test_capture_success_stores_fresh(tmp_path, monkeypatch):
    database = db.init_db(f"sqlite:///{(tmp_path / 'w.db').as_posix()}")
    with db.session_scope(database) as conn:
        pid = _plot(conn)
        monkeypatch.setattr(
            "app.weather.snapshots.fetch_forecast_72h_rain",
            lambda **kw: 6.5)
        snap = capture_weather_snapshot(conn, pid)
        assert snap.availability == "fresh"
        assert snap.rain72_mm == 6.5
        got = latest_weather_snapshot(conn, pid)
        assert got is not None and got.availability == "fresh"
        payload = weather_state_payload(conn, pid)
        assert payload["availability"] == "fresh"
        assert payload["rain72_mm"] == 6.5


def test_capture_failure_never_zero(tmp_path, monkeypatch):
    database = db.init_db(f"sqlite:///{(tmp_path / 'w2.db').as_posix()}")
    with db.session_scope(database) as conn:
        pid = _plot(conn)

        def boom(**kw):
            raise RuntimeError("BMKG offline")

        monkeypatch.setattr(
            "app.weather.snapshots.fetch_forecast_72h_rain", boom)
        snap = capture_weather_snapshot(conn, pid)
        assert snap.availability == "unavailable"
        assert snap.rain72_mm is None  # never 0.0 for a failure
        payload = weather_state_payload(conn, pid)
        assert payload["availability"] == "unavailable"
        assert payload["rain72_mm"] is None
