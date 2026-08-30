from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import default_db_url

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plots (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    variety TEXT NOT NULL DEFAULT '',
    area_ha REAL NOT NULL DEFAULT 1.0,
    transplant_date DATE NOT NULL,
    pipe_zero_cm REAL NOT NULL DEFAULT 30.0,
    scaled INTEGER NOT NULL DEFAULT 0,
    lat REAL,
    lon REAL,
    bmkg_adm4 TEXT,
    is_demo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bmkg_areas (
    kode_wilayah TEXT PRIMARY KEY,
    nama_wilayah TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_bmkg_areas_nama ON bmkg_areas(nama_wilayah);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY,
    plot_id INTEGER NOT NULL REFERENCES plots(id),
    ts TEXT NOT NULL,
    dist_cm REAL NOT NULL,
    level_cm REAL NOT NULL,
    batt_v REAL
);
CREATE INDEX IF NOT EXISTS ix_readings_plot_ts ON readings(plot_id, ts);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY,
    plot_id INTEGER NOT NULL REFERENCES plots(id),
    ts TEXT NOT NULL,
    stage TEXT NOT NULL,
    level_cm REAL NOT NULL,
    action TEXT NOT NULL,
    reason_id TEXT NOT NULL,
    rain72_mm REAL
);
CREATE INDEX IF NOT EXISTS ix_decisions_plot_ts ON decisions(plot_id, ts);

CREATE TABLE IF NOT EXISTS irrigations (
    id INTEGER PRIMARY KEY,
    plot_id INTEGER NOT NULL REFERENCES plots(id),
    ts TEXT NOT NULL,
    volume_m3 REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_irrigations_plot_ts ON irrigations(plot_id, ts);

CREATE TABLE IF NOT EXISTS vision_reports (
    id INTEGER PRIMARY KEY,
    plot_id INTEGER REFERENCES plots(id),
    ts TEXT NOT NULL,
    image_path TEXT NOT NULL,
    top_class TEXT NOT NULL,
    confidence REAL NOT NULL,
    severity TEXT NOT NULL,
    language TEXT NOT NULL,
    advisory_json TEXT NOT NULL,
    fusion_json TEXT,
    is_demo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_trace_json TEXT
);

-- Created here (not only in the L1 migration) so Task 1.1's snapshot
-- service can run against init_db() before Task 2.1 lands; the 0002
-- migration's CREATE TABLE for this table then becomes a no-op.
CREATE TABLE IF NOT EXISTS weather_snapshots (
    id INTEGER PRIMARY KEY,
    plot_id INTEGER NOT NULL REFERENCES plots(id),
    source TEXT NOT NULL,
    adm4 TEXT,
    fetched_at TEXT NOT NULL,
    window_end TEXT NOT NULL,
    rain72_mm REAL,
    availability TEXT NOT NULL,
    stale_since TEXT,
    demo INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_weather_snapshots_plot
    ON weather_snapshots(plot_id, id);
"""


def sqlite_path_from_url(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError(f"only sqlite:/// URLs are supported, got: {url}")
    return Path(url[len(prefix):])


class Database:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or default_db_url()
        self.path = sqlite_path_from_url(self.url)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            _ensure_plot_columns(conn)


_default: Database | None = None


def init_db(url: str | None = None) -> Database:
    global _default
    _default = Database(url)
    _default.init_db()
    return _default


def get_db() -> Database:
    if _default is None:
        init_db()
    assert _default is not None
    return _default


@contextmanager
def session_scope(db: Database | None = None) -> Iterator[sqlite3.Connection]:
    conn = (db or get_db()).connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_plot_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(plots)")}
    if "bmkg_adm4" not in cols:
        conn.execute("ALTER TABLE plots ADD COLUMN bmkg_adm4 TEXT")


# ---------------------------------------------------------------------------
# Row helpers (thin, explicit SQL - PhyToSignal storage.py style)
# ---------------------------------------------------------------------------

def get_plot(conn: sqlite3.Connection, plot_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM plots WHERE id = ?", (plot_id,)).fetchone()


def get_plot_by_name(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM plots WHERE name = ?", (name,)).fetchone()


def create_plot(conn: sqlite3.Connection, *, name: str, transplant_date: str,
                variety: str = "", area_ha: float = 1.0,
                pipe_zero_cm: float = 30.0, scaled: bool = False,
                lat: float | None = None, lon: float | None = None,
                bmkg_adm4: str | None = None,
                is_demo: bool = True) -> int:
    cur = conn.execute(
        """
        INSERT INTO plots (name, variety, area_ha, transplant_date,
                           pipe_zero_cm, scaled, lat, lon, bmkg_adm4, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, variety, area_ha, transplant_date, pipe_zero_cm,
         int(scaled), lat, lon, bmkg_adm4, int(is_demo)),
    )
    return int(cur.lastrowid)


def update_plot_bmkg_adm4(conn: sqlite3.Connection, plot_id: int,
                          bmkg_adm4: str) -> None:
    conn.execute("UPDATE plots SET bmkg_adm4 = ? WHERE id = ?",
                 (bmkg_adm4, plot_id))


def insert_reading(conn: sqlite3.Connection, *, plot_id: int, ts: str,
                   dist_cm: float, level_cm: float,
                   batt_v: float | None = None) -> None:
    conn.execute(
        "INSERT INTO readings (plot_id, ts, dist_cm, level_cm, batt_v)"
        " VALUES (?, ?, ?, ?, ?)",
        (plot_id, ts, dist_cm, level_cm, batt_v),
    )


def insert_decision(conn: sqlite3.Connection, *, plot_id: int, ts: str,
                    stage: str, level_cm: float, action: str,
                    reason_id: str, rain72_mm: float | None = None) -> None:
    conn.execute(
        "INSERT INTO decisions (plot_id, ts, stage, level_cm, action,"
        " reason_id, rain72_mm) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (plot_id, ts, stage, level_cm, action, reason_id, rain72_mm),
    )


def insert_irrigation(conn: sqlite3.Connection, *, plot_id: int, ts: str,
                      volume_m3: float) -> None:
    conn.execute(
        "INSERT INTO irrigations (plot_id, ts, volume_m3) VALUES (?, ?, ?)",
        (plot_id, ts, volume_m3),
    )


def latest_reading(conn: sqlite3.Connection, plot_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM readings WHERE plot_id = ? ORDER BY ts DESC LIMIT 1",
        (plot_id,),
    ).fetchone()


def latest_decision(conn: sqlite3.Connection, plot_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM decisions WHERE plot_id = ? ORDER BY ts DESC LIMIT 1",
        (plot_id,),
    ).fetchone()


def count_rows(conn: sqlite3.Connection, table: str,
               plot_id: int | None = None) -> int:
    if plot_id is None:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
    else:
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE plot_id = ?",
            (plot_id,),
        ).fetchone()
    return int(row["n"])


def delete_demo_rows(conn: sqlite3.Connection) -> int:
    """Remove every demo row so the seeder can re-insert cleanly.

    Non-demo rows are never touched. Returns the number of demo plots removed.
    """
    ids = [r["id"] for r in
           conn.execute("SELECT id FROM plots WHERE is_demo = 1").fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(
        f"DELETE FROM irrigations WHERE plot_id IN ({qmarks})", ids)
    conn.execute(
        f"DELETE FROM decisions WHERE plot_id IN ({qmarks})", ids)
    conn.execute(
        f"DELETE FROM readings WHERE plot_id IN ({qmarks})", ids)
    conn.execute(
        f"DELETE FROM vision_reports WHERE plot_id IN ({qmarks})"
        " OR is_demo = 1", ids)
    conn.execute(f"DELETE FROM plots WHERE id IN ({qmarks})", ids)
    return len(ids)
