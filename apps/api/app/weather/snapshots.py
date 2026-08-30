"""Weather snapshot persistence with explicit availability states.

Availability is one of: fresh, stale-cache, unavailable.
A BMKG fetch failure is NEVER stored as 0 mm: rain72_mm stays None and
availability becomes "unavailable" with provenance (WEA-003).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.irrigation.weather_bmkg import DEFAULT_ADM4, fetch_forecast_72h_rain

_WEATHER_TTL_S = 15 * 60.0


@dataclass
class WeatherSnapshot:
    id: int | None
    plot_id: int
    source: str
    adm4: str | None
    fetched_at: str
    window_end: str
    rain72_mm: float | None
    availability: str
    stale_since: str | None
    demo: bool


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _window_end(fetched_at: str) -> str:
    return (datetime.fromisoformat(fetched_at)
            + timedelta(hours=72)).isoformat()


def _row_to_snapshot(row) -> WeatherSnapshot:
    return WeatherSnapshot(
        id=int(row["id"]), plot_id=int(row["plot_id"]),
        source=row["source"], adm4=row["adm4"],
        fetched_at=row["fetched_at"], window_end=row["window_end"],
        rain72_mm=(float(row["rain72_mm"])
                   if row["rain72_mm"] is not None else None),
        availability=row["availability"],
        stale_since=row["stale_since"], demo=bool(row["demo"]))


def capture_weather_snapshot(conn, plot_id: int, adm4: str | None = None,
                             *, demo: bool = True) -> WeatherSnapshot:
    """Fetch BMKG for the plot's area and store a snapshot row.

    A failed fetch stores availability='unavailable' with rain72_mm=None.
    """
    from app.config import get_settings

    code = adm4 or get_settings().bmkg_adm4 or DEFAULT_ADM4
    fetched_at = _utc_now_iso()
    try:
        rain = fetch_forecast_72h_rain(adm4=code)
        availability = "fresh"
        rain72 = round(float(rain), 1)
        stale_since = None
    except Exception:
        availability = "unavailable"
        rain72 = None
        stale_since = _utc_now_iso()
    cur = conn.execute(
        "INSERT INTO weather_snapshots (plot_id, source, adm4, fetched_at,"
        " window_end, rain72_mm, availability, stale_since, demo)"
        " VALUES (?, 'BMKG', ?, ?, ?, ?, ?, ?, ?)",
        (plot_id, code, fetched_at, _window_end(fetched_at), rain72,
         availability, stale_since, int(demo)))
    return WeatherSnapshot(id=int(cur.lastrowid), plot_id=plot_id,
                           source="BMKG", adm4=code, fetched_at=fetched_at,
                           window_end=_window_end(fetched_at),
                           rain72_mm=rain72, availability=availability,
                           stale_since=stale_since, demo=demo)


def latest_weather_snapshot(conn, plot_id: int) -> WeatherSnapshot | None:
    row = conn.execute(
        "SELECT * FROM weather_snapshots WHERE plot_id = ?"
        " ORDER BY id DESC LIMIT 1", (plot_id,)).fetchone()
    return _row_to_snapshot(row) if row is not None else None


def _is_stale(snap: WeatherSnapshot) -> bool:
    if snap.availability != "fresh":
        return False
    fetched = datetime.fromisoformat(snap.fetched_at)
    return (datetime.now(timezone.utc) - fetched).total_seconds() > _WEATHER_TTL_S


def weather_state_payload(conn, plot_id: int) -> dict:
    """Current weather state for the plot (fresh | stale-cache | unavailable)."""
    snap = latest_weather_snapshot(conn, plot_id)
    if snap is None:
        return {"source": "BMKG", "adm4": None, "availability": "unavailable",
                "rain72_mm": None, "fetched_at": None, "window_end": None,
                "stale_since": None,
                "secondary_review": {"needs_review": True}}
    availability = snap.availability
    stale_since = snap.stale_since
    if availability == "fresh" and _is_stale(snap):
        availability = "stale-cache"
        stale_since = snap.fetched_at
    return {"source": snap.source, "adm4": snap.adm4,
            "availability": availability, "rain72_mm": snap.rain72_mm,
            "fetched_at": snap.fetched_at, "window_end": snap.window_end,
            "stale_since": stale_since,
            "secondary_review": {"needs_review": availability != "fresh"}}
