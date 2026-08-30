# apps/api/tests/test_l1_integration.py
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import db
from app import main as main_mod

_WIB = timezone(timedelta(hours=7))


def test_l1_full_loop(tmp_path, monkeypatch):
    db.init_db(f"sqlite:///{(tmp_path / 'l1int.db').as_posix()}")
    monkeypatch.setattr(
        "app.weather.snapshots.fetch_forecast_72h_rain",
        lambda **kw: 20.0)
    monkeypatch.setattr("app.assistant.agent.chat",
                        lambda session_id, messages, client=None: {
                            "reply": "Sesuai rekomendasi tersimpan, tunggu hujan.",
                            "tool_trace": [], "mode": "offline"})
    c = TestClient(main_mod.app)

    # transplant = today(WIB) - 30 d keeps the plot in the veg stage
    # (day 30 -> Stage.VEG_AWD), matching the demo seeder convention; the
    # brief's pinned date drifts into FLOWERING_LOCK as real time passes,
    # where HOLD_FOR_RAIN can never fire (see task-4.6 report ruling).
    transplant = (datetime.now(_WIB).date() - timedelta(days=30)).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Petak Uji",
                             transplant_date=transplant, is_demo=False)

    # 1. manual observation -> recommendation (rain 20 mm, veg stage
    #    level -16.0 <= trigger -15.0 and above hard floor -25.0:
    #    HOLD_FOR_RAIN; the brief's -8.0 sits above the trigger and WAITs)
    body = c.post(f"/api/v1/plots/{pid}/water-observations",
                  json={"level_cm": -16.0, "source": "manual"}).json()
    assert body["recommendation"]["action"] == "HOLD_FOR_RAIN"
    rec_id = body["recommendation"]["id"]

    # 2. confirmation
    conf = c.post(f"/api/v1/recommendations/{rec_id}/confirmations",
                  json={"status": "deferred", "note": "tunggu hujan"}).json()
    assert conf["confirmations"][0]["status"] == "deferred"

    # 3. evidence separation
    e3 = c.get("/api/v1/evidence/e3").json()
    vision = c.get("/api/v1/evidence/vision").json()
    assert e3["label"] != vision["label"]
    assert e3["label"] == "DEFINED SIMULATION"
    assert vision["label"] == "PUBLIC-DATASET BENCHMARK"

    # 4. assistant explains stored records (offline, mocked)
    chat = c.post("/api/assistant/chat",
                  json={"session_id": "s1",
                        "messages": [{"role": "user",
                                      "content": "Kenapa tunggu?"}]}).json()
    assert chat["mode"] == "offline"

    # 5. audit trail rows exist
    with db.session_scope() as conn:
        n_rec = conn.execute(
            "SELECT COUNT(*) AS n FROM recommendations WHERE plot_id = ?",
            (pid,)).fetchone()["n"]
        n_conf = conn.execute(
            "SELECT COUNT(*) AS n FROM action_confirmations"
            " WHERE recommendation_id = ?", (rec_id,)).fetchone()["n"]
    assert n_rec == 1
    assert n_conf == 1
