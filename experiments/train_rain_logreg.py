"""Fit a tiny LogReg on Open-Meteo daily rain for Salatiga.

Target: next 72 h precipitation >= 15 mm.
Features: intercept, yesterday rain, last-3-day rain, sin/cos day-of-year.

Writes apps/api/app/irrigation/rain_logreg.json
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "api" / "app" / "irrigation" / "rain_logreg.json"
LAT, LON = -7.331, 110.508
THRESH = 15.0


def _sigmoid(z):
    z = np.clip(z, -30, 30)
    return 1.0 / (1.0 + np.exp(-z))


def fit_logreg(x: np.ndarray, y: np.ndarray, steps: int = 400, lr: float = 0.05) -> np.ndarray:
    w = np.zeros(x.shape[1], dtype=np.float64)
    n = max(1, x.shape[0])
    for _ in range(steps):
        p = _sigmoid(x @ w)
        grad = x.T @ (p - y) / n
        w -= lr * grad
    return w


def main() -> None:
    start, end = "2018-01-01", date.today().isoformat()
    r = httpx.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": LAT, "longitude": LON,
            "start_date": start, "end_date": end,
            "daily": "precipitation_sum",
            "timezone": "Asia/Jakarta",
        },
        timeout=60.0,
        headers={"User-Agent": "IRIS/1.0 (INOVATALK 2026)"},
    )
    r.raise_for_status()
    daily = r.json()["daily"]
    precip = [float(v or 0.0) for v in daily["precipitation_sum"]]
    dates = daily["time"]
    rows_x, rows_y = [], []
    for i in range(3, len(precip) - 3):
        if precip[i] is None:
            continue
        rain_1 = precip[i - 1]
        rain_3 = precip[i - 1] + precip[i - 2] + precip[i - 3]
        future = precip[i] + precip[i + 1] + precip[i + 2]
        y = 1.0 if future >= THRESH else 0.0
        dt = date.fromisoformat(dates[i])
        doy = dt.timetuple().tm_yday
        ang = 2.0 * math.pi * ((doy - 1) % 365) / 365.0
        rows_x.append([1.0, rain_1, rain_3, math.sin(ang), math.cos(ang)])
        rows_y.append(y)
    x = np.asarray(rows_x, dtype=np.float64)
    y = np.asarray(rows_y, dtype=np.float64)
    w = fit_logreg(x, y)
    p = _sigmoid(x @ w)
    pred = (p >= 0.5).astype(float)
    acc = float((pred == y).mean())
    pos = float(y.mean())
    blob = {
        "weights": [round(float(v), 6) for v in w],
        "feature_order": ["bias", "rain_1d_mm", "rain_3d_mm", "sin_doy", "cos_doy"],
        "target": "next_72h_precip_ge_15mm",
        "n": int(len(y)),
        "base_rate_wet": round(pos, 4),
        "train_accuracy": round(acc, 4),
        "source": "Open-Meteo ERA5-land daily precipitation, Salatiga",
        "latitude": LAT,
        "longitude": LON,
        "start": start,
        "end": end,
        "notes": [
            "Second opinion only. BMKG remains the scheduler rain input.",
            "Not a BMKG replacement and not a field rain gauge.",
        ],
    }
    OUT.write_text(json.dumps(blob, indent=2), encoding="utf-8")
    print(json.dumps({k: blob[k] for k in ("n", "base_rate_wet", "train_accuracy", "weights")}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
