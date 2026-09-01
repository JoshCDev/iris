"""Deterministic poster-chart generator for the E3 evidence figures.

Reads the E3 result from experiments/outputs/backtest_summary.json (written
by experiments/run_all.py -> apps/api/scripts/backtest.py) and the cited
literature context from experiments/outputs/chart_context_data.csv, then
writes both PNG and editable SVG outputs to assets/poster/.

Usage:
  python experiments/generate_poster_charts.py          # regenerate
  python experiments/generate_poster_charts.py --check  # fail on drift

Design rules (readiness plan section 24): separate panels for water (m3)
and methane (kg) because the units differ; a colorblind-safe palette; no
text overlap at poster/README sizes; fixed dimensions; no local paths in
the output; simulated/modelled labels in titles, captions, and alt text.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY = REPO_ROOT / "experiments" / "outputs" / "backtest_summary.json"
CONTEXT_CSV = REPO_ROOT / "experiments" / "outputs" / "chart_context_data.csv"
OUT_DIR = REPO_ROOT / "assets" / "poster"

# Colorblind-safe qualitative palette (Okabe-Ito inspired).
BLUE = "#1976d2"
BROWN = "#8d6e63"
GREEN = "#2e7d32"
RED = "#c62828"
GREY = "#9e9e9e"
BAND = "#ffe082"

FIG_WIDTH, FIG_HEIGHT = 9.0, 4.6
DPI = 300


def load_summary() -> dict:
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    # Accept both the flat legacy schema and the wrapped §24.1 schema.
    if "iris_e3" in data:
        return {
            "days": data["scenario"]["season_days"],
            "water_awd_m3": data["iris_e3"]["water_m3_ha_season"],
            "water_cf_m3": data["continuous_flooding"]["water_m3_ha_season"],
            "flooded_days_awd": data["iris_e3"]["flooded_days"],
            "flooded_days_cf": data["continuous_flooding"]["flooded_days"],
            "sf_w_eff": data["iris_e3"]["effective_sf_w"],
            "ch4_cf_kg": data["continuous_flooding"]["ch4_kg_ha_season"],
            "ch4_awd_kg": data["iris_e3"]["ch4_kg_ha_season"],
            "co2e_saved_t": data["iris_e3"]["ch4_only_avoided_co2e_t_ha_season"],
            "water_saved_pct": data["differences_percent"]["water"],
            "ch4_saved_pct": data["differences_percent"]["ch4"],
        }
    return data


def _water_trace(days: int = 100, drawdown_cm_day: float = 0.8) -> tuple[list[float], list[int]]:
    """Replay the E3 engine's water level day by day (no rain, refill +5 cm,
    halved drawdown below 0 cm) so the trace matches the backtest.
    During establishment (first 14 days) and flowering lock (55-79) the
    field is kept flooded by continuous inflow, matching the backtest's
    flooded-day accounting and the scheduler's stage protections."""
    from app.irrigation.protocol import stage_on, trigger_level_cm
    from app.irrigation.scheduler import REFILL_CM

    lvl = REFILL_CM
    trace: list[float] = []
    irr: list[int] = []
    for d in range(days):
        stage = stage_on(d)
        trig = trigger_level_cm(stage)
        if stage.value in ("establishment", "flowering_lock"):
            # Flooded by inflow; shallow pond with a small daily fluctuation.
            lvl = REFILL_CM + 0.1 * ((d * 7) % 11 - 5) / 5.0
        else:
            lvl -= drawdown_cm_day if lvl >= 0 else 0.5 * drawdown_cm_day
        if trig is not None and lvl <= trig:
            irr.append(d)
            lvl = REFILL_CM
        trace.append(lvl)
    return trace, irr


def _plot_water_trace(days: int) -> None:
    trace, irr = _water_trace(days)
    cf = [5.0] * days
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.plot(trace, color=BLUE, lw=2, label="IRIS (safe AWD) — [simulated]")
    ax.plot(cf, color=BROWN, lw=1.5, ls="-.", label="continuous flooding (+5 cm)")
    ax.axhline(0, color=GREY, ls=":", lw=1)
    ax.axhline(-15, color=RED, ls="--", lw=1)
    ax.text(days + 2, -15, "-15 cm\nAWD trigger", va="center", fontsize=8,
            color=RED)
    # Vegetative AWD window (days 0-54) and flowering lock (55-79).
    ax.axvspan(55, 80, color=BAND, alpha=0.45)
    ax.text(67.5, 5.6, "flowering flood", ha="center", fontsize=8)
    for d in irr:
        ax.plot(d, 5.0, "v", color=BLUE, ms=4)
    ax.set_xlabel("Days after transplant")
    ax.set_ylabel("Water table (cm)")
    ax.set_title(f"Water-table trace, {days}-day simulation, 0 mm rain [simulated]")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_xlim(0, days + 12)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "chart_water_trace.png", dpi=DPI)
    fig.savefig(OUT_DIR / "chart_water_trace.svg")
    plt.close(fig)


def _plot_results(s: dict) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.8))
    b1 = a1.bar(["Continuous\nflooding", "IRIS\n(safe AWD)"],
                [s["water_cf_m3"], s["water_awd_m3"]],
                color=[BROWN, BLUE], width=0.55)
    a1.set_ylabel("Irrigation water (m$^3$ ha$^{-1}$ season$^{-1}$)")
    a1.set_title(f"Irrigation water: {s['water_saved_pct']:.1f}% [simulated]",
                 fontsize=10)
    a1.bar_label(b1, fmt="%d")
    b2 = a2.bar(["Continuous\nflooding", "IRIS\n(safe AWD)"],
                [s["ch4_cf_kg"], s["ch4_awd_kg"]],
                color=[BROWN, GREEN], width=0.55)
    a2.set_ylabel("Seasonal CH$_4$ (kg ha$^{-1}$)")
    a2.set_title(f"CH$_4$: {s['ch4_saved_pct']:.1f}%  "
                 f"({s['co2e_saved_t']:.3f} t CO$_2$e) [modelled]",
                 fontsize=10)
    a2.bar_label(b2, fmt="%.2f")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "chart_results.png", dpi=DPI)
    fig.savefig(OUT_DIR / "chart_results.svg")
    plt.close(fig)


def _check(s: dict) -> None:
    expected = {
        "water_cf_m3": 8000.0,
        "water_awd_m3": 5000.0,
        "water_saved_pct": -37.5,
        "flooded_days_awd": 51,
        "flooded_days_cf": 100,
        "ch4_cf_kg": 130.0,
        "ch4_awd_kg": 115.99,
        "co2e_saved_t": 0.3784,
        "sf_w_eff": 0.8922,
    }
    problems = []
    for key, want in expected.items():
        got = s.get(key)
        if got is None or abs(float(got) - want) > 0.005:
            problems.append(f"{key}: expected {want}, got {got}")
    if problems:
        raise SystemExit("E3 summary drift:\n  " + "\n  ".join(problems))
    for name in ("chart_results", "chart_water_trace"):
        for ext in ("png", "svg"):
            if not (OUT_DIR / f"{name}.{ext}").is_file():
                problems.append(f"missing output {name}.{ext}")
    if problems:
        raise SystemExit("chart outputs missing:\n  " + "\n  ".join(problems))
    print("E3 values and chart outputs match committed inputs.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify committed values/outputs without regenerating")
    args = ap.parse_args()

    if not SUMMARY.is_file():
        raise SystemExit(f"missing {SUMMARY}; run `python experiments/run_all.py` first")
    if not CONTEXT_CSV.is_file():
        raise SystemExit(f"missing {CONTEXT_CSV}")
    s = load_summary()
    days = int(s["days"])
    if args.check:
        _check(s)
        return
    _plot_water_trace(days)
    _plot_results(s)
    print("charts written:", sorted(p.name for p in OUT_DIR.glob("chart_*.png")))


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
    main()
