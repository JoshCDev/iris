from datetime import datetime, timedelta, timezone

from app import db
from app.db_l1 import (
    insert_action_confirmation,
    insert_leaf_assessment,
    insert_recommendation,
    insert_water_observation,
    insert_weather_snapshot_row,
)
from scripts.seed_demo import (AREA_HA, DAYS, LAT, LON, PIPE_ZERO_CM,
                               PLOT_NAME, RAIN72_MM, RAIN_EVENT_DAYS,
                               TOTAL_STEPS, _transplant_date, seed_demo)

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
    s1 = seed_demo(url)
    first_run = _rows(url)
    s2 = seed_demo(url)
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
    seed_demo(ua)
    seed_demo(ub)
    ra, rb = _rows(ua), _rows(ub)
    assert ra[2][0]["ts"] == rb[2][0]["ts"]
    assert [r["ts"] for r in ra[2]] == [r["ts"] for r in rb[2]]


def test_seed_hold_for_rain_only_with_wet_forecast(tmp_path):
    url = f"sqlite:///{(tmp_path / 'e.db').as_posix()}"
    summary = seed_demo(url)
    assert summary["hold_for_rain"] >= 1
    _, _, _, decisions, _, _ = _rows(url)
    holds = [d for d in decisions if d["action"] == "HOLD_FOR_RAIN"]
    assert all(float(d["rain72_mm"]) >= 15.0 for d in holds)
    hold_days = {datetime.fromisoformat(d["ts"]).astimezone(WIB).timetuple()
                 .tm_yday for d in holds}
    event_days = {
        (_transplant_date() + timedelta(days=n)).timetuple().tm_yday
        for n in RAIN_EVENT_DAYS}
    assert hold_days <= event_days


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
    # Re-seed must succeed (the reported failure) and leave L1 tables empty.
    summary = seed_demo(url)
    assert summary["replaced_plots"] == 1
    with db.session_scope(db.Database(url)) as conn:
        for table in ("water_observations", "recommendations",
                      "action_confirmations", "weather_snapshots",
                      "leaf_assessments"):
            assert db.count_rows(conn, table) == 0


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
