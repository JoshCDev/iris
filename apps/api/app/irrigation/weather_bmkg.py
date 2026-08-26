"""72-hour rain forecast from BMKG open weather data.

Endpoint and field names follow https://data.bmkg.go.id/prakiraan-cuaca
(same pattern as ResponCepat `BMKGWeatherService.php`):
`GET https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={kode}`.

adm4 is the Kemendagri level-IV code from area_code_part1-4.pdf.
Default 33.73.01.1003 is Kelurahan Salatiga, Kecamatan Sidorejo, Kota
Salatiga (area_code_part2.pdf). Precipitation is the `tp` field (mm)
on each 3-hour slot; three forecast days are summed for rain72.

Attribution: BMKG must be named as the data source in the UI.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

FORECAST_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
DEFAULT_ADM4 = "33.73.01.1003"


def parse_bmkg_forecast(payload: dict) -> float:
    """Sum `tp` (mm) across all forecast slots. Fail-soft on bad cells."""
    total = 0.0
    for area in payload.get("data") or []:
        if not isinstance(area, dict):
            continue
        for day in area.get("cuaca") or []:
            slots = day if isinstance(day, list) else [day]
            for item in slots:
                if not isinstance(item, dict):
                    continue
                try:
                    total += float(item.get("tp") or 0.0)
                except (TypeError, ValueError):
                    continue
    return round(total, 1)


def _timeout_s() -> float:
    try:
        return get_settings().bmkg_timeout_s
    except Exception:
        return 20.0


def _forecast_payload(adm4: str) -> dict:
    settings = get_settings()
    headers = {
        "User-Agent": "IRIS/1.0 (INOVATALK 2026; Universitas Kristen Maranatha)",
        "Accept": "application/json",
    }
    if settings.bmkg_api_key:
        headers["X-API-Key"] = settings.bmkg_api_key
    r = httpx.get(
        FORECAST_URL,
        params={"adm4": adm4},
        headers=headers,
        timeout=_timeout_s(),
    )
    r.raise_for_status()
    return r.json()


def fetch_forecast_72h_rain(lat: float | None = None,
                            lon: float | None = None) -> float:
    """Return 72 h rainfall (mm). lat/lon kept for call-site compatibility."""
    del lat, lon
    adm4 = get_settings().bmkg_adm4 or DEFAULT_ADM4
    return parse_bmkg_forecast(_forecast_payload(adm4))
