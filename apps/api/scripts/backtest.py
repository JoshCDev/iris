import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.engine import run_backtest  # noqa: E402


def _wrap(result, rain_mm: float, scaled: bool) -> dict:
    """§24.1 schema: explicit scenario, units, and evidence labels."""
    d = asdict(result)
    return {
        "schema_version": 1,
        "scenario_id": "E3",
        "scenario": {
            "season_days": d["days"],
            "area_ha": 1.0,
            "rain_mm": rain_mm,
            "drawdown_cm_per_day": 0.8,
            "negative_level_drawdown_multiplier": 0.5,
            "refill_level_cm": 5.0,
            "live_rain_hold_applied": False,
            "scaled": scaled,
        },
        "continuous_flooding": {
            "water_m3_ha_season": d["water_cf_m3"],
            "flooded_days": d["flooded_days_cf"],
            "ch4_kg_ha_season": d["ch4_cf_kg"],
        },
        "iris_e3": {
            "water_m3_ha_season": d["water_awd_m3"],
            "flooded_days": d["flooded_days_awd"],
            "effective_sf_w": d["sf_w_eff"],
            "ch4_kg_ha_season": d["ch4_awd_kg"],
            "ch4_only_avoided_co2e_t_ha_season": d["co2e_saved_t"],
        },
        "differences_percent": {
            "water": -d["water_saved_pct"],
            "ch4": round(
                (1 - d["ch4_awd_kg"] / d["ch4_cf_kg"]) * 100, 2)
            if d["ch4_cf_kg"] else 0.0,
        },
        "evidence_labels": {
            "water": "simulated",
            "ch4": "modelled",
            "co2e": "modelled_ch4_only",
        },
        "_legacy_flat": d,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="E3 backtest AWD vs continuous flooding")
    ap.add_argument("--days", type=int, default=100)
    ap.add_argument("--drawdown", type=float, default=0.8)
    ap.add_argument("--rain-mm", type=float, default=0.0)
    ap.add_argument("--area-ha", type=float, default=1.0)
    ap.add_argument("--scaled", action="store_true")
    args = ap.parse_args()
    result = run_backtest(days=args.days, drawdown_cm_day=args.drawdown,
                          rain_series=[args.rain_mm] * args.days,
                          area_ha=args.area_ha, scaled=args.scaled)
    payload = json.dumps(_wrap(result, args.rain_mm, args.scaled), indent=2)
    print(payload)
    out = (Path(__file__).resolve().parents[3] / "experiments" / "outputs"
           / "backtest_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
