import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.engine import run_backtest


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
    payload = json.dumps(asdict(result), indent=2)
    print(payload)
    out = (Path(__file__).resolve().parents[3] / "experiments" / "outputs"
           / "backtest_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
