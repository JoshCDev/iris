"""Load Kemendagri level-IV codes into SQLite for BMKG adm4 lookup."""
from __future__ import annotations

import gzip
import json
import sqlite3
from pathlib import Path

AREAS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "bmkg_areas.json.gz"
)


def load_area_rows(path: Path | None = None) -> list[list[str]]:
    src = path or AREAS_PATH
    if not src.is_file():
        return []
    opener = gzip.open if src.suffix == ".gz" or src.name.endswith(".json.gz") \
        else open
    with opener(src, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    rows: list[list[str]] = []
    for item in data:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            rows.append([str(item[0]), str(item[1])])
    return rows


def ensure_bmkg_areas(conn: sqlite3.Connection,
                      path: Path | None = None) -> int:
    """Insert area rows if the table is empty. Returns row count after."""
    n = conn.execute("SELECT COUNT(*) AS n FROM bmkg_areas").fetchone()["n"]
    if int(n) > 0:
        return int(n)
    rows = load_area_rows(path)
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR IGNORE INTO bmkg_areas (kode_wilayah, nama_wilayah)"
        " VALUES (?, ?)",
        rows,
    )
    return int(conn.execute("SELECT COUNT(*) AS n FROM bmkg_areas")
               .fetchone()["n"])


def lookup_bmkg_areas(conn: sqlite3.Connection, query: str,
                      limit: int = 20) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    if len(q.split(".")) >= 4:
        rows = conn.execute(
            "SELECT kode_wilayah, nama_wilayah FROM bmkg_areas"
            " WHERE kode_wilayah = ? LIMIT ?",
            (q, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT kode_wilayah, nama_wilayah FROM bmkg_areas"
            " WHERE nama_wilayah LIKE ? COLLATE NOCASE"
            " ORDER BY length(nama_wilayah) ASC LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
    return [{"kode_wilayah": r["kode_wilayah"],
             "nama_wilayah": r["nama_wilayah"]} for r in rows]
