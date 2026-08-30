import sqlite3

from app import db


def test_l1_tables_exist_after_init(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    db.init_db(url)
    conn = sqlite3.connect((tmp_path / "m.db").as_posix())
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("water_observations", "weather_snapshots", "recommendations",
              "action_confirmations", "leaf_assessments", "evidence_runs"):
        assert t in tables
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(recommendations)")}
    for c in ("plot_id", "observation_id", "weather_snapshot_id", "stage",
              "action", "reason_codes", "ruleset_version", "needs_review",
              "created_at", "superseded_at", "demo"):
        assert c in cols
    conn.close()
