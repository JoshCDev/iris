"""BMKG area catalog load/lookup. Uses a tiny fixture, not the full dump."""
import gzip
import json
from pathlib import Path

from app import db
from app.irrigation.bmkg_areas import ensure_bmkg_areas, lookup_bmkg_areas


def _write_fixture(path: Path) -> Path:
    rows = [
        ["33.73.01.1003", "Salatiga"],
        ["33.73.01.1002", "Sidorejo Lor"],
        ["31.71.03.1001", "Kemayoran"],
    ]
    gz = path / "bmkg_areas.json.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh)
    return gz


def test_ensure_and_lookup_by_name_and_code(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'a.db').as_posix()}")
    gz = _write_fixture(tmp_path)
    with db.session_scope() as conn:
        assert ensure_bmkg_areas(conn, gz) == 3
        assert ensure_bmkg_areas(conn, gz) == 3
        by_name = lookup_bmkg_areas(conn, "Salatiga")
        assert by_name[0]["kode_wilayah"] == "33.73.01.1003"
        by_code = lookup_bmkg_areas(conn, "31.71.03.1001")
        assert by_code[0]["nama_wilayah"] == "Kemayoran"


def test_empty_query_returns_nothing(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'b.db').as_posix()}")
    with db.session_scope() as conn:
        assert lookup_bmkg_areas(conn, "") == []
        assert lookup_bmkg_areas(conn, "   ") == []
