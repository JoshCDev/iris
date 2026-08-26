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


def test_default_dump_path_points_at_api_data():
    from app.irrigation.bmkg_areas import AREAS_PATH, load_area_rows
    assert AREAS_PATH.name == "bmkg_areas.json.gz"
    assert AREAS_PATH.parent.name == "data"
    assert AREAS_PATH.parent.parent.name == "api"
    rows = load_area_rows()
    assert any(code == "33.73.01.1003" for code, _name in rows)


def test_weather_areas_endpoint_uses_catalog(tmp_path, monkeypatch):
    import app.irrigation.bmkg_areas as areas
    import app.main as main_mod
    from fastapi.testclient import TestClient

    gz = _write_fixture(tmp_path)
    monkeypatch.setattr(areas, "AREAS_PATH", gz)
    db.init_db(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    client = TestClient(main_mod.app)
    empty = client.get("/api/weather/areas", params={"q": ""})
    assert empty.status_code == 200
    assert empty.json() == {"results": []}
    hit = client.get("/api/weather/areas", params={"q": "Salatiga"})
    assert hit.status_code == 200
    assert hit.json()["results"][0]["kode_wilayah"] == "33.73.01.1003"
    by_code = client.get("/api/weather/areas", params={"q": "31.71.03.1001"})
    assert by_code.json()["results"][0]["nama_wilayah"] == "Kemayoran"


def test_patch_plot_bmkg_adm4(tmp_path, monkeypatch):
    import app.irrigation.bmkg_areas as areas
    import app.main as main_mod
    from fastapi.testclient import TestClient

    gz = _write_fixture(tmp_path)
    monkeypatch.setattr(areas, "AREAS_PATH", gz)
    db.init_db(f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    with db.session_scope() as conn:
        pid = db.create_plot(
            conn, name="P", transplant_date="2026-01-01",
            bmkg_adm4="33.73.01.1003")
    client = TestClient(main_mod.app)
    ok = client.patch(f"/api/plots/{pid}", json={"bmkg_adm4": "31.71.03.1001"})
    assert ok.status_code == 200
    assert ok.json()["nama_wilayah"] == "Kemayoran"
    bad = client.patch(f"/api/plots/{pid}", json={"bmkg_adm4": "00.00.00.0000"})
    assert bad.status_code == 400
    missing = client.patch("/api/plots/999", json={"bmkg_adm4": "31.71.03.1001"})
    assert missing.status_code == 404
