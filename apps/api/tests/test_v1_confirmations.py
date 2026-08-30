import json

from fastapi.testclient import TestClient

from app import db
from app import main as main_mod


def _client(tmp_path, monkeypatch):
    db.init_db(f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain",
        lambda **kw: 6.5)
    return TestClient(main_mod.app)


def _rec(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak",
                             transplant_date="2026-07-01", is_demo=False)
    body = c.post(f"/api/v1/plots/{pid}/water-observations",
                  json={"level_cm": -15.2, "source": "manual"}).json()
    return c, pid, body["recommendation"]["id"]


def test_confirmation_does_not_mutate_recommendation(tmp_path, monkeypatch):
    c, pid, rec_id = _rec(tmp_path, monkeypatch)
    before = c.get(f"/api/v1/recommendations/{rec_id}").json()
    r = c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
               json={"status": "performed", "volume_m3": 12.5,
                     "note": "irrigated at dawn"})
    assert r.status_code == 200
    body = r.json()
    # ACT-003: the recommendation row is never mutated by a confirmation.
    assert body["recommendation"] == before["recommendation"]
    assert body["recommendation"]["action"] == "IRRIGATE"
    # reason_codes is the stored JSON-encoded list, passed through raw
    # (deviation from the brief's `["AWD_TRIGGER_REACHED"]` — the scheduler
    # stores human-readable reason text; see task-2.4 report ruling).
    reason_codes = json.loads(body["recommendation"]["reason_codes"])
    assert isinstance(reason_codes, list) and len(reason_codes) == 1
    assert len(body["confirmations"]) == 1
    assert body["confirmations"][0]["status"] == "performed"
    assert body["confirmations"][0]["volume_m3"] == 12.5


def test_confirmation_unknown_status_rejected(tmp_path, monkeypatch):
    c, pid, rec_id = _rec(tmp_path, monkeypatch)
    r = c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
               json={"status": "maybe"})
    assert r.status_code == 422


def test_confirmations_are_append_only(tmp_path, monkeypatch):
    c, pid, rec_id = _rec(tmp_path, monkeypatch)
    c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
           json={"status": "deferred", "note": "wait for rain"})
    c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
           json={"status": "performed"})
    body = c.get(f"/api/v1/recommendations/{rec_id}").json()
    assert len(body["confirmations"]) == 2
    assert [x["status"] for x in body["confirmations"]] == ["deferred", "performed"]
