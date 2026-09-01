# Invokes the ported engine via apps/api/scripts/backtest.py (subprocess:
# cleaner than sys.path bootstrap - CLI owns its own import setup).
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
SCRIPT = API / "scripts" / "backtest.py"
OUT = ROOT / "experiments" / "outputs" / "backtest_summary.json"


def main() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=str(API))
    data = json.loads(OUT.read_text(encoding="utf-8"))
    flat = data.get("_legacy_flat", data)
    cols = ["days", "irrigations_awd", "irrigations_cf", "water_awd_m3",
            "water_cf_m3", "flooded_days_awd", "flooded_days_cf", "sf_w_eff",
            "ch4_cf_kg", "ch4_awd_kg", "co2e_saved_t", "water_saved_pct"]
    width = max(len(c) for c in cols) + 2
    for c in cols:
        print(f"{c:<{width}}{flat[c]}")
    print(f"summary: {OUT}")


if __name__ == "__main__":
    main()
