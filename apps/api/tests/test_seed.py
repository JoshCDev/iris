import json
from datetime import datetime, timedelta, timezone

import pytest

from app import db
from app.db_l1 import (
    insert_action_confirmation,
    insert_leaf_assessment,
    insert_recommendation,
    insert_water_observation,
    insert_weather_snapshot_row,
)
from scripts.seed_demo import (AREA_HA, DAYS, LAT, LON, PIPE_ZERO_CM,
                               PLOT_NAME, RAIN72_MM, TOTAL_STEPS,
                               _transplant_date, seed_demo)

WIB = timezone(timedelta(hours=7))


def _rows(db_url):
    database = db.init_db(db_url)
    with db.session_scope(database) as conn:
        plots = conn.execute("SELECT * FROM plots").fetchall()
        readings = conn.execute(
            "SELECT * FROM readings ORDER BY ts ASC").fetchall()
        decisions = conn.execute("SELECT * FROM decisions").fetchall()
        irrigations = conn.execute("SELECT * FROM irrigations").fetchall()
        holds = conn.execute(
            "SELECT COUNT(*) AS n FROM decisions WHERE action ="
            " 'HOLD_FOR_RAIN'").fetchone()["n"]
        return (database, [dict(p) for p in plots],
                [dict(r) for r in readings],
                [dict(d) for d in decisions],
                [dict(i) for i in irrigations], int(holds))


def test_seed_contract_counts_and_plot(tmp_path):
    url = f"sqlite:///{(tmp_path / 'a.db').as_posix()}"
    summary = seed_demo(url)
    assert summary["readings"] == TOTAL_STEPS == 2880
    assert summary["decisions"] == 2880
    assert summary["hold_for_rain"] >= 1
    _, plots, readings, _, _, _ = _rows(url)
    assert len(plots) == 1
    plot = plots[0]
    assert plot["name"] == PLOT_NAME
    assert plot["is_demo"] == 1
    assert abs(plot["area_ha"] - AREA_HA) < 1e-9
    assert abs(plot["pipe_zero_cm"] - PIPE_ZERO_CM) < 1e-9
    assert abs(plot["lat"] - LAT) < 1e-9
    assert abs(plot["lon"] - LON) < 1e-9
    assert plot["bmkg_adm4"] == "33.73.01.1003"
    expected_transplant = _transplant_date().isoformat()
    assert plot["transplant_date"] == expected_transplant
    assert len(readings) == 2880


def test_seed_deterministic_seed_twice_same_db(tmp_path):
    url = f"sqlite:///{(tmp_path / 'b.db').as_posix()}"
    fixed_now = datetime(2026, 8, 31, 6, 0, tzinfo=WIB)
    s1 = seed_demo(url, now=fixed_now)
    first_run = _rows(url)
    s2 = seed_demo(url, now=fixed_now)
    second_run = _rows(url)
    assert s1["readings"] == s2["readings"]
    assert s1["irrigations"] == s2["irrigations"]
    assert s1["hold_for_rain"] == s2["hold_for_rain"]
    # identical first reading ts + identical series content
    assert first_run[2][0]["ts"] == second_run[2][0]["ts"]
    assert [r["level_cm"] for r in first_run[2]] == \
        [r["level_cm"] for r in second_run[2]]
    assert [d["action"] for d in first_run[3]] == \
        [d["action"] for d in second_run[3]]
    # idempotent: still exactly one demo plot
    assert len(first_run[1]) == len(second_run[1]) == 1


def test_seed_deterministic_across_databases(tmp_path):
    ua = f"sqlite:///{(tmp_path / 'c.db').as_posix()}"
    ub = f"sqlite:///{(tmp_path / 'd.db').as_posix()}"
    fixed_now = datetime(2026, 8, 31, 6, 0, tzinfo=WIB)
    seed_demo(ua, now=fixed_now)
    seed_demo(ub, now=fixed_now)
    ra, rb = _rows(ua), _rows(ub)
    assert ra[2][0]["ts"] == rb[2][0]["ts"]
    assert [r["ts"] for r in ra[2]] == [r["ts"] for r in rb[2]]


def test_seed_series_ends_at_seed_time(tmp_path):
    """The grid is anchored to seed time, so the last reading is current —
    no hole grows between the demo data and the moment of viewing."""
    url = f"sqlite:///{(tmp_path / 'now.db').as_posix()}"
    seed_demo(url)
    _, _, readings, _, _, _ = _rows(url)
    last = datetime.fromisoformat(readings[-1]["ts"])
    now_wib = datetime.now(WIB)
    age_minutes = (now_wib - last).total_seconds() / 60.0
    assert 0 <= age_minutes <= 16  # within one 15-min step of seeding


def test_seed_hold_for_rain_only_with_wet_forecast(tmp_path):
    url = f"sqlite:///{(tmp_path / 'e.db').as_posix()}"
    summary = seed_demo(url)
    assert summary["hold_for_rain"] >= 1
    _, _, _, decisions, _, _ = _rows(url)
    holds = [d for d in decisions if d["action"] == "HOLD_FOR_RAIN"]
    assert all(float(d["rain72_mm"]) >= 15.0 for d in holds)
    # Holds may only occur on days where the wet forecast was present.
    wet_days = {
        datetime.fromisoformat(d["ts"]).astimezone(WIB).timetuple().tm_yday
        for d in decisions if float(d["rain72_mm"]) >= 15.0}
    hold_days = {datetime.fromisoformat(d["ts"]).astimezone(WIB).timetuple()
                 .tm_yday for d in holds}
    assert hold_days <= wet_days


def test_seed_readings_grid_and_bands(tmp_path):
    url = f"sqlite:///{(tmp_path / 'f.db').as_posix()}"
    seed_demo(url)
    _, plots, readings, _, _, _ = _rows(url)
    pipe_zero = plots[0]["pipe_zero_cm"]
    levels = [float(r["level_cm"]) for r in readings]
    assert max(levels) <= 5.5
    assert min(levels) > -25.01
    for a, b in zip(readings, readings[1:]):
        ta = datetime.fromisoformat(a["ts"])
        tb = datetime.fromisoformat(b["ts"])
        assert (tb - ta).total_seconds() == 900.0
        break
    gaps_ok = all(
        (datetime.fromisoformat(b["ts"]) - datetime.fromisoformat(a["ts"]))
        .total_seconds() == 900.0
        for a, b in zip(readings[:200], readings[1:200]))
    assert gaps_ok
    for r in readings:
        assert abs((pipe_zero - float(r["level_cm"]))
                   - float(r["dist_cm"])) <= 0.005
        if r["batt_v"] is not None:
            assert 3.8 <= float(r["batt_v"]) <= 4.1


def test_seed_idempotent_preserves_non_demo_rows(tmp_path):
    url = f"sqlite:///{(tmp_path / 'g.db').as_posix()}"
    seed_demo(url)
    with db.session_scope(db.Database(url)) as conn:
        real_pid = db.create_plot(conn, name="Sawah Petani Asli",
                                  transplant_date=_transplant_date()
                                  .isoformat(), is_demo=False)
        db.insert_reading(conn, plot_id=real_pid,
                          ts=datetime.now(timezone.utc).isoformat(),
                          dist_cm=35.0, level_cm=-5.0)
    summary = seed_demo(url)
    with db.session_scope(db.Database(url)) as conn:
        plots = conn.execute("SELECT * FROM plots ORDER BY id").fetchall()
        names = {p["name"] for p in plots}
        assert names == {PLOT_NAME, "Sawah Petani Asli"}
        assert db.count_rows(conn, "readings", real_pid) == 1
    assert summary["replaced_plots"] == 1


def test_reseed_cleans_l1_rows(tmp_path):
    """Re-seeding a demo plot that has L1 rows (water_observations,
    recommendations, action_confirmations, weather_snapshots,
    leaf_assessments) must not trip the FK constraint (CTX-005)."""
    url = f"sqlite:///{(tmp_path / 'l1.db').as_posix()}"
    seed_demo(url)
    with db.session_scope(db.Database(url)) as conn:
        pid = conn.execute(
            "SELECT id FROM plots WHERE is_demo = 1").fetchone()["id"]
        obs = insert_water_observation(
            conn, plot_id=pid, source="manual", level_cm=-15.2,
            observed_at="2026-08-30T07:15:00+07:00",
            received_at="2026-08-30T07:15:01+07:00")
        snap = insert_weather_snapshot_row(
            conn, plot_id=pid, source="bmkg", adm4="33.73.01.1003",
            fetched_at="2026-08-30T07:00:00+07:00",
            window_end="2026-08-30T07:00:00+07:00", rain72_mm=0.0,
            availability="ok")
        rec = insert_recommendation(
            conn, plot_id=pid, observation_id=obs, weather_snapshot_id=snap,
            stage="veg_awd", action="WAIT", reason_codes='["SAFE"]',
            ruleset_version="safe-awd-v1",
            created_at="2026-08-30T07:15:02+07:00")
        insert_action_confirmation(
            conn, recommendation_id=rec, status="performed",
            created_at="2026-08-30T08:30:00+07:00", volume_m3=12.5)
        insert_leaf_assessment(
            conn, plot_id=pid, image_hash="abc123", retention_mode="operational",
            model_version="rice-v1", guard_result="ok", class_="blast",
            confidence=0.92, severity="medium",
            created_at="2026-08-30T08:00:00+07:00")
    # Re-seed must succeed (the reported failure), clear the manually
    # inserted L1 rows, and repopulate the seeder's own v1 records at full
    # cadence (one observation/snapshot/recommendation per reading step).
    summary = seed_demo(url)
    assert summary["replaced_plots"] == 1
    with db.session_scope(db.Database(url)) as conn:
        # Manual rows (confirmation + leaf assessment) are gone; the seeder
        # re-created its own leaf assessments.
        assert db.count_rows(conn, "action_confirmations") == 0
        assert db.count_rows(conn, "leaf_assessments") == 2
        # The v1 mirror exists at full cadence (one per simulated reading;
        # the grid ends at seed time, so no extra anchor row is needed).
        assert db.count_rows(conn, "water_observations") == TOTAL_STEPS
        assert db.count_rows(conn, "recommendations") == TOTAL_STEPS
        assert db.count_rows(conn, "weather_snapshots") == TOTAL_STEPS


def test_seed_v1_records_consistent_with_legacy(tmp_path):
    """The v1 mirror must tell the SAME story as the legacy tables: the
    latest v1 recommendation matches the latest legacy decision, only the
    latest recommendation is current (rest superseded), and every row is
    demo-marked."""
    url = f"sqlite:///{(tmp_path / 'v1c.db').as_posix()}"
    seed_demo(url)
    with db.session_scope(db.Database(url)) as conn:
        pid = conn.execute(
            "SELECT id FROM plots WHERE is_demo = 1").fetchone()["id"]
        latest_legacy = conn.execute(
            "SELECT action, reason_id, level_cm, ts FROM decisions"
            " WHERE plot_id = ? ORDER BY ts DESC, id DESC LIMIT 1",
            (pid,)).fetchone()
        latest_rec = conn.execute(
            "SELECT action, reason_codes, created_at, superseded_at, demo"
            " FROM recommendations WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        assert latest_rec is not None
        assert latest_rec["action"] == latest_legacy["action"]
        assert json.loads(latest_rec["reason_codes"]) == [latest_legacy["reason_id"]]
        assert latest_rec["superseded_at"] is None
        assert latest_rec["demo"] == 1
        # Exactly one current recommendation; the rest carry superseded_at.
        current = conn.execute(
            "SELECT COUNT(*) AS n FROM recommendations WHERE plot_id = ?"
            " AND superseded_at IS NULL", (pid,)).fetchone()["n"]
        superseded = conn.execute(
            "SELECT COUNT(*) AS n FROM recommendations WHERE plot_id = ?"
            " AND superseded_at IS NOT NULL", (pid,)).fetchone()["n"]
        assert current == 1
        assert superseded == TOTAL_STEPS - 1
        # The latest v1 observation matches the latest legacy reading level.
        latest_obs = conn.execute(
            "SELECT level_cm, demo FROM water_observations WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        latest_reading = conn.execute(
            "SELECT level_cm FROM readings WHERE plot_id = ?"
            " ORDER BY ts DESC, id DESC LIMIT 1", (pid,)).fetchone()
        assert latest_obs["level_cm"] == pytest.approx(
            float(latest_reading["level_cm"]))
        assert latest_obs["demo"] == 1


def test_seed_engine_paths_real_decisions(tmp_path):
    url = f"sqlite:///{(tmp_path / 'h.db').as_posix()}"
    seed_demo(url)
    _, _, _, decisions, irrigations, _ = _rows(url)
    actions = {d["action"] for d in decisions}
    assert {"WAIT", "IRRIGATE", "HOLD_FOR_RAIN"} <= actions
    assert all(d["stage"] in ("establishment", "veg_awd") for d in decisions)
    for i in irrigations:
        assert float(i["volume_m3"]) > 0.0
    assert len(irrigations) >= 1
