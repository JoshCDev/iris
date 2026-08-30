"""Row helpers for the L1 domain tables (raw SQL, app.db style)."""
from __future__ import annotations

import sqlite3


def insert_water_observation(conn, *, plot_id: int, source: str,
                             level_cm: float, observed_at: str,
                             received_at: str, raw_distance: float | None = None,
                             actor: str | None = None,
                             quality_state: str = "ok",
                             demo: bool = True) -> int:
    cur = conn.execute(
        "INSERT INTO water_observations (plot_id, source, raw_distance,"
        " level_cm, calibration_id, actor, observed_at, received_at,"
        " quality_state, demo) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)",
        (plot_id, source, raw_distance, level_cm, actor, observed_at,
         received_at, quality_state, int(demo)))
    return int(cur.lastrowid)


def insert_weather_snapshot_row(conn, *, plot_id: int, source: str,
                                adm4: str | None, fetched_at: str,
                                window_end: str, rain72_mm: float | None,
                                availability: str,
                                stale_since: str | None = None,
                                demo: bool = True) -> int:
    cur = conn.execute(
        "INSERT INTO weather_snapshots (plot_id, source, adm4, fetched_at,"
        " window_end, rain72_mm, availability, stale_since, demo)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (plot_id, source, adm4, fetched_at, window_end, rain72_mm,
         availability, stale_since, int(demo)))
    return int(cur.lastrowid)


def insert_recommendation(conn, *, plot_id: int, observation_id: int,
                          weather_snapshot_id: int | None, stage: str,
                          action: str, reason_codes: str,
                          ruleset_version: str, created_at: str,
                          needs_review: bool = False,
                          demo: bool = True) -> int:
    cur = conn.execute(
        "INSERT INTO recommendations (plot_id, observation_id,"
        " weather_snapshot_id, stage, action, reason_codes, ruleset_version,"
        " needs_review, created_at, superseded_at, demo)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
        (plot_id, observation_id, weather_snapshot_id, stage, action,
         reason_codes, ruleset_version, int(needs_review), created_at,
         int(demo)))
    return int(cur.lastrowid)


def latest_recommendation(conn, plot_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM recommendations WHERE plot_id = ?"
        " ORDER BY id DESC LIMIT 1", (plot_id,)).fetchone()


def supersede_older_recommendations(conn, plot_id: int, keep_id: int,
                                    superseded_at: str) -> int:
    cur = conn.execute(
        "UPDATE recommendations SET superseded_at = ?"
        " WHERE plot_id = ? AND id != ? AND superseded_at IS NULL",
        (superseded_at, plot_id, keep_id))
    return cur.rowcount


def insert_action_confirmation(conn, *, recommendation_id: int,
                               status: str, created_at: str,
                               actor_id: int | None = None,
                               action_at: str | None = None,
                               volume_m3: float | None = None,
                               note: str | None = None,
                               demo: bool = True) -> int:
    cur = conn.execute(
        "INSERT INTO action_confirmations (recommendation_id, actor_id,"
        " status, action_at, volume_m3, note, created_at, demo)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (recommendation_id, actor_id, status, action_at, volume_m3, note,
         created_at, int(demo)))
    return int(cur.lastrowid)


def recommendation_with_confirmations(conn, recommendation_id: int) -> dict | None:
    rec = conn.execute(
        "SELECT * FROM recommendations WHERE id = ?",
        (recommendation_id,)).fetchone()
    if rec is None:
        return None
    rows = conn.execute(
        "SELECT * FROM action_confirmations WHERE recommendation_id = ?"
        " ORDER BY id ASC", (recommendation_id,)).fetchall()
    return {"recommendation": dict(rec),
            "confirmations": [dict(r) for r in rows]}


def insert_evidence_run(conn, *, type_: str, version: str,
                        parameters_json: str, outputs_json: str,
                        generated_at: str, demo: bool = True) -> int:
    cur = conn.execute(
        "INSERT INTO evidence_runs (type, version, parameters_json,"
        " outputs_json, generated_at, demo) VALUES (?, ?, ?, ?, ?, ?)",
        (type_, version, parameters_json, outputs_json, generated_at,
         int(demo)))
    return int(cur.lastrowid)


def latest_leaf_assessment(conn, plot_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM leaf_assessments WHERE plot_id = ?"
        " ORDER BY id DESC LIMIT 1", (plot_id,)).fetchone()
