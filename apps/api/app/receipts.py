import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from app.irrigation.ipcc import GreenReceipt, build_receipt

_REPO = Path(__file__).resolve().parents[3]
E3_SUMMARY_PATH = _REPO / "experiments" / "outputs" / "backtest_summary.json"

E3_CLAIM_NOTE = (
    "Season claim from E3 backtest (100 days, 0 mm rain, 1 ha) "
    "[simulated]. The 30-day demo plot is not used for the season claim."
)
PLOT_CLAIM_NOTE = (
    "Computed from this plot's window, not the E3 poster claim. "
    "Do not read this as a 100-day season result."
)


def render_text(r: GreenReceipt, extra_note: str | None = None) -> str:
    lines = [
        "== IRIS GREEN RECEIPT ==",
        f"Plot: {r.plot_name}",
        f"Season: {r.season_days} days [{r.label}]",
        f"Water saved: {r.water_saved_m3:,.0f} m3 ({r.water_saved_pct:.1f}%)",
        f"CH4 avoided: {r.ch4_saved_kg:,.1f} kg",
        f"CO2e equivalent: {r.co2e_saved_t:,.3f} t",
        f"Effective SF_w: {r.sf_w_effective}",
        "Method: IPCC Tier-1 (see docs/IPCC_ACCOUNTING.md)",
    ]
    if extra_note:
        lines.append(extra_note)
    return "\n".join(lines)


def render_png(r: GreenReceipt, path: str) -> str:
    img = Image.new("RGB", (900, 600), "#f2f7f2")
    d = ImageDraw.Draw(img)
    y = 40
    for ln in render_text(r).splitlines():
        d.rectangle([30, y - 6, 870, y + 34], fill="#ffffff")
        d.text((44, y), ln[:70], fill="#123d2b")
        y += 52
    img.save(path, "PNG")
    return path


def load_e3_summary() -> dict[str, Any]:
    return json.loads(E3_SUMMARY_PATH.read_text(encoding="utf-8"))


def build_e3_receipt(plot_name: str) -> GreenReceipt:
    """Season-claim receipt pinned to the committed E3 backtest (1 ha)."""
    data = load_e3_summary()
    return build_receipt(
        plot_name=plot_name,
        season_days=int(data["scenario"]["season_days"]),
        flooded_days=int(data["iris_e3"]["flooded_days"]),
        water_baseline_m3=float(data["continuous_flooding"]["water_m3_ha_season"]),
        water_actual_m3=float(data["iris_e3"]["water_m3_ha_season"]),
        area_ha=float(data["scenario"]["area_ha"]),
        label="simulated",
    )


def receipt_json(plot_id: int, receipt: GreenReceipt, *,
                 claim_source: str, claim_note: str) -> dict[str, Any]:
    return {
        "plot_id": plot_id,
        "label": receipt.label,
        "season_days": receipt.season_days,
        "flooded_days": receipt.flooded_days,
        "aerated_days": receipt.aerated_days,
        "sf_w_effective": receipt.sf_w_effective,
        "water_baseline_m3": receipt.water_baseline_m3,
        "water_actual_m3": receipt.water_actual_m3,
        "water_saved_m3": receipt.water_saved_m3,
        "water_saved_pct": receipt.water_saved_pct,
        "ch4_baseline_kg": receipt.ch4_baseline_kg,
        "ch4_actual_kg": receipt.ch4_actual_kg,
        "ch4_saved_kg": receipt.ch4_saved_kg,
        "co2e_saved_t": receipt.co2e_saved_t,
        "text": render_text(receipt, extra_note=claim_note),
        "claim_source": claim_source,
        "claim_note": claim_note,
    }
