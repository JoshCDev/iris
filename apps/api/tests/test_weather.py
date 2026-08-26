"""BMKG forecast parser. No network."""
import json
from pathlib import Path

from app.irrigation.weather_bmkg import parse_bmkg_forecast

FIX = Path(__file__).resolve().parent / "fixtures" / "bmkg_salatiga.json"


def test_parse_bmkg_fixture_sums_tp():
    payload = json.loads(FIX.read_text(encoding="utf-8"))
    assert parse_bmkg_forecast(payload) == 7.0


def test_parse_bmkg_empty_is_zero():
    assert parse_bmkg_forecast({}) == 0.0
    assert parse_bmkg_forecast({"data": []}) == 0.0


def test_parse_bmkg_ignores_bad_tp():
    payload = {"data": [{"cuaca": [[{"tp": "x"}, {"tp": 1.5}]]}]}
    assert parse_bmkg_forecast(payload) == 1.5
