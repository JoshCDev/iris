from app import db
from app.db_l1 import (
    insert_action_confirmation,
    insert_recommendation,
    insert_water_observation,
    latest_recommendation,
    supersede_older_recommendations,
)


def _seed(tmp_path):
    database = db.init_db(f"sqlite:///{(tmp_path / 'l1.db').as_posix()}")
    with db.session_scope(database) as conn:
        pid = db.create_plot(conn, name="Petak", transplant_date="2026-01-01")
        obs_id = insert_water_observation(
            conn, plot_id=pid, source="manual", level_cm=-15.2,
            observed_at="2026-08-30T07:15:00+07:00",
            received_at="2026-08-30T07:15:01+07:00")
        rec1 = insert_recommendation(
            conn, plot_id=pid, observation_id=obs_id,
            weather_snapshot_id=None, stage="veg_awd", action="IRRIGATE",
            reason_codes='["AWD_TRIGGER_REACHED"]',
            ruleset_version="safe-awd-v1", created_at="2026-08-30T07:15:02+07:00")
        return pid, obs_id, rec1


def test_insert_and_latest_recommendation(tmp_path):
    pid, obs_id, rec1 = _seed(tmp_path)
    with db.session_scope() as conn:
        latest = latest_recommendation(conn, pid)
        assert latest is not None
        assert latest["action"] == "IRRIGATE"
        assert latest["observation_id"] == obs_id


def test_supersede_keeps_history(tmp_path):
    pid, obs_id, rec1 = _seed(tmp_path)
    with db.session_scope() as conn:
        obs2 = insert_water_observation(
            conn, plot_id=pid, source="manual", level_cm=-5.0,
            observed_at="2026-08-30T08:00:00+07:00",
            received_at="2026-08-30T08:00:01+07:00")
        rec2 = insert_recommendation(
            conn, plot_id=pid, observation_id=obs2,
            weather_snapshot_id=None, stage="veg_awd", action="WAIT",
            reason_codes='["SAFE"]', ruleset_version="safe-awd-v1",
            created_at="2026-08-30T08:00:02+07:00")
        n = supersede_older_recommendations(
            conn, pid, keep_id=rec2, superseded_at="2026-08-30T08:00:02+07:00")
        assert n == 1
        row = conn.execute(
            "SELECT superseded_at FROM recommendations WHERE id = ?",
            (rec1,)).fetchone()
        assert row["superseded_at"] is not None


def test_insert_confirmation_links(tmp_path):
    pid, obs_id, rec1 = _seed(tmp_path)
    with db.session_scope() as conn:
        cid = insert_action_confirmation(
            conn, recommendation_id=rec1, status="performed",
            created_at="2026-08-30T08:30:00+07:00", volume_m3=12.5)
        row = conn.execute(
            "SELECT * FROM action_confirmations WHERE id = ?", (cid,)).fetchone()
        assert row["status"] == "performed"
        assert row["volume_m3"] == 12.5
