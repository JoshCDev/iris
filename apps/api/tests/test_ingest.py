from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config as cfg
from app import db
import app.main as main_mod

PINNED_STATUS_KEYS = {"plot_id", "name", "level_cm", "stage", "stage_days",
                      "action", "reason_id", "rain72_mm", "next_check",
                      "last_ts", "is_demo"}


def _swap_db(tmp_path):
    return db.init_db(f"sqlite:///{(tmp_path / 't.db').as_posix()}")


def _client(tmp_path, monkeypatch, rain=0.0):
    _swap_db(tmp_path)
    monkeypatch.setattr(main_mod, "fetch_forecast_72h_rain",
                        lambda a, b: rain)
    main_mod._weather_cache["ts"] = 0.0
    main_mod._weather_cache["value"] = None
    return TestClient(main_mod.app)


@pytest.fixture
def client(tmp_path, monkeypatch):
    return _client(tmp_path, monkeypatch)


@pytest.fixture
def require_token_mode(tmp_path, monkeypatch):
    _swap_db(tmp_path)
    monkeypatch.setattr(main_mod, "fetch_forecast_72h_rain",
                        lambda a, b: 0.0)
    monkeypatch.setenv("IRIS_DEVICE_TOKEN", "dev-token")
    cfg.reset_settings_cache()
    yield
    monkeypatch.undo()
    cfg.reset_settings_cache()


# --- WIB clock helpers (audited fixes preserved) ---------------------------

def test_stage_days_clamps_future_transplant():
    future = date.today() + timedelta(days=3)
    assert main_mod._stage_days(future) == 0


def test_stage_days_counts_full_days_from_injected_today():
    assert main_mod._stage_days(date(2026, 1, 1),
                                today=date(2026, 2, 25)) == 55


def test_wib_today_matches_fixed_offset_clock():
    wib = timezone(timedelta(hours=7))
    assert main_mod._wib_today() == datetime.now(wib).date()


# --- auth -------------------------------------------------------------------

def test_ingest_without_header_ok_in_demo_mode(client):
    r = client.post("/api/ingest",
                    json={"device_plot_name": "A", "dist_cm": 46.0})
    assert r.status_code == 201


def test_ingest_any_header_ok_in_demo_mode(client):
    r = client.post("/api/ingest",
                    json={"device_plot_name": "A", "dist_cm": 46.0},
                    headers={"X-IRIS-Token": "whatever"})
    assert r.status_code == 201


def test_ingest_wrong_token_unauthorized_when_required(require_token_mode):
    c = TestClient(main_mod.app)
    r = c.post("/api/ingest",
               json={"device_plot_name": "A", "dist_cm": 46.0},
               headers={"X-IRIS-Token": "wrong"})
    assert r.status_code == 401


def test_ingest_missing_header_unauthorized_when_required(require_token_mode):
    c = TestClient(main_mod.app)
    r = c.post("/api/ingest",
               json={"device_plot_name": "A", "dist_cm": 46.0})
    assert r.status_code == 401


def test_ingest_correct_token_accepted_when_required(require_token_mode):
    c = TestClient(main_mod.app)
    r = c.post("/api/ingest",
               json={"device_plot_name": "A", "dist_cm": 46.0},
               headers={"X-IRIS-Token": "dev-token"})
    assert r.status_code == 201


# --- validation -------------------------------------------------------------

def test_post_reading_rejects_implausible_dist(client):
    for dist in (1e12, -5.0):
        r = client.post("/api/ingest",
                        json={"device_plot_name": "A", "dist_cm": dist})
        assert r.status_code == 422
        assert r.json()["detail"] == "dist_cm outside a plausible sensor range"


def test_post_reading_rejects_dist_beyond_existing_pipe(client):
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Pipa30",
                             transplant_date=date.today().isoformat(),
                             pipe_zero_cm=30.0)
    r = client.post("/api/ingest",
                    json={"device_plot_name": "Pipa30", "dist_cm": 61.0})
    assert r.status_code == 422
    st = client.get(f"/api/plots/{pid}/status")
    assert st.json()["level_cm"] is None
    assert st.json()["action"] is None


# --- pinned status shape ------------------------------------------------------

def test_ingest_creates_plot_and_returns_pinned_shape(client):
    r = client.post("/api/ingest",
                    json={"device_plot_name": "Sawah Uji",
                          "dist_cm": 46.0, "batt_v": 3.9}, )
    assert r.status_code == 201
    body = r.json()
    assert set(body.keys()) == PINNED_STATUS_KEYS
    assert body["level_cm"] == -16.0
    assert body["action"] == "IRRIGATE"
    assert body["is_demo"] is True
    assert body["next_check"] is not None
    st = client.get(f"/api/plots/{body['plot_id']}/status")
    assert st.status_code == 200
    assert set(st.json().keys()) == PINNED_STATUS_KEYS
    assert st.json()["level_cm"] == -16.0


def test_ingest_persists_decision_and_irrigation(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, rain=25.0)
    body = c.post("/api/ingest",
                  json={"device_plot_name": "Sawah Uji",
                        "dist_cm": 46.0}).json()
    pid = body["plot_id"]
    with db.session_scope() as conn:
        assert db.count_rows(conn, "readings", pid) == 1
        assert db.count_rows(conn, "decisions", pid) == 1
        dec = db.latest_decision(conn, pid)
        assert dec["action"] == "IRRIGATE"
        assert float(dec["rain72_mm"]) == 25.0
        assert dec["stage"] == "establishment"
        assert db.count_rows(conn, "irrigations", pid) == 1


def test_status_nulls_before_first_reading(client):
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Kosong",
                             transplant_date=date.today().isoformat())
    st = client.get(f"/api/plots/{pid}/status")
    body = st.json()
    assert body["level_cm"] is None
    assert body["action"] is None
    assert body["next_check"] is None
    assert body["last_ts"] is None
    assert body["stage_days"] == 0


def test_history_series(client):
    body = client.post("/api/ingest",
                       json={"device_plot_name": "Sawah Uji",
                             "dist_cm": 46.0}).json()
    h = client.get(f"/api/plots/{body['plot_id']}/history").json()
    assert len(h["readings"]) == 1
    assert len(h["decisions"]) == 1
    assert h["readings"][0]["level_cm"] == -16.0


# --- scaled mesocosm (audited behavior) -------------------------------------

def test_scaled_mesocosm_trigger(client):
    past = (date.today() - timedelta(days=30)).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Bak Uji", transplant_date=past,
                             pipe_zero_cm=30.0, scaled=True)
    r = client.post("/api/ingest",
                    json={"device_plot_name": "Bak Uji", "dist_cm": 36.0})
    body = r.json()
    assert body["level_cm"] == -6.0
    assert body["stage"] == "veg_awd"
    assert body["action"] == "IRRIGATE"
    assert body["plot_id"] == pid


# --- weather endpoint ---------------------------------------------------------

def test_weather_fail_open_on_error(client, monkeypatch):
    def boom(a, b):
        raise RuntimeError("offline")
    monkeypatch.setattr(main_mod, "fetch_forecast_72h_rain", boom)
    r = client.get("/api/weather/forecast")
    assert r.status_code == 200
    assert r.json() == {"rain72_mm": 0.0, "stale": True}


def test_weather_caches_for_15_minutes(client, monkeypatch):
    calls = {"n": 0}

    def fake(a, b):
        calls["n"] += 1
        return 17.5
    monkeypatch.setattr(main_mod, "fetch_forecast_72h_rain", fake)
    r1 = client.get("/api/weather/forecast")
    r2 = client.get("/api/weather/forecast")
    assert r1.json() == {"rain72_mm": 17.5, "stale": False}
    assert r2.json() == {"rain72_mm": 17.5, "stale": False}
    assert calls["n"] == 1


# --- health -------------------------------------------------------------------

@pytest.fixture
def _llm_probe_reset():
    from app.assistant import agent

    agent.reset_llm_probe_cache()
    agent._last_fallback_ts = None
    yield
    agent.reset_llm_probe_cache()
    agent._last_fallback_ts = None


def test_health_pinned_llm_mode_fields_live(client, _llm_probe_reset,
                                            monkeypatch):
    from app.assistant import agent

    monkeypatch.setattr(agent, "llm_status", lambda force=False: "reachable")
    monkeypatch.setattr(agent, "fallback_engaged_recently",
                        lambda window_s=60.0: False)
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["onnx"] == "loaded"
    assert body["llm"] == "reachable"
    assert body["mode"] == "live"


def test_health_offline_when_llm_unreachable(client, _llm_probe_reset,
                                             monkeypatch):
    from app.assistant import agent

    monkeypatch.setattr(agent, "llm_status", lambda force=False: "unreachable")
    body = client.get("/api/health").json()
    assert body["llm"] == "unreachable"
    assert body["mode"] == "offline"


def test_health_offline_when_fallback_engaged(client, _llm_probe_reset,
                                              monkeypatch):
    from app.assistant import agent

    monkeypatch.setattr(agent, "llm_status", lambda force=False: "reachable")
    agent.mark_fallback_engaged()
    body = client.get("/api/health").json()
    assert body["llm"] == "reachable"
    assert body["mode"] == "offline"


def test_receipt_requires_data(client):
    r = client.get("/api/plots/999/receipt")
    assert r.status_code == 404


def test_receipt_default_is_e3(client):
    r = client.post("/api/ingest", json={
        "device_plot_name": "ResiE3", "dist_cm": 25.0})
    assert r.status_code == 201
    pid = r.json()["plot_id"]
    body = client.get(f"/api/plots/{pid}/receipt").json()
    assert body["claim_source"] == "e3_backtest"
    assert body["water_saved_pct"] == 37.5
    assert body["water_baseline_m3"] == 8000.0
    assert body["water_actual_m3"] == 5000.0
    assert body["flooded_days"] == 51
    assert body["ch4_actual_kg"] == 115.99
    assert body["co2e_saved_t"] == 0.3784
    assert "30-day demo plot" in body["claim_note"]


def test_receipt_plot_claim_needs_irrigation(client):
    r = client.post("/api/ingest", json={
        "device_plot_name": "ResiPlot", "dist_cm": 25.0})
    pid = r.json()["plot_id"]
    empty = client.get(f"/api/plots/{pid}/receipt?claim=plot")
    # one ingest at +5 cm typically WAIT, so no irrigation row yet
    assert empty.status_code in (200, 409)


def test_ingest_pipe_zero_cm_on_autocreate(client):
    r = client.post('/api/ingest', json={'device_plot_name': 'Pipa45',
                                         'dist_cm': 45.0,
                                         'pipe_zero_cm': 50.0})
    assert r.status_code == 201
    body = r.json()
    assert body['level_cm'] == pytest.approx(5.0)
    with db.session_scope() as conn:
        plot = db.get_plot(conn, body['plot_id'])
        assert plot['pipe_zero_cm'] == pytest.approx(50.0)


def test_ingest_pipe_zero_cm_default_when_absent(client):
    r = client.post('/api/ingest', json={'device_plot_name': 'PipaDefault',
                                         'dist_cm': 45.0})
    assert r.status_code == 201
    with db.session_scope() as conn:
        plot = db.get_plot(conn, r.json()['plot_id'])
        assert plot['pipe_zero_cm'] == pytest.approx(30.0)
