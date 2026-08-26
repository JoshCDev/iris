from dataclasses import dataclass

from app.irrigation.protocol import stage_on, trigger_level_cm
from app.irrigation.scheduler import REFILL_CM
from app.irrigation.ipcc import (SF_W_CONTINUOUS, co2e_t, effective_sf_w,
                                 seasonal_ch4_kg)
from app.irrigation.water import level_cm_to_m3


@dataclass
class BacktestResult:
    days: int
    irrigations_awd: int
    irrigations_cf: int
    water_awd_m3: float
    water_cf_m3: float
    flooded_days_awd: int
    flooded_days_cf: int
    sf_w_eff: float
    ch4_cf_kg: float
    ch4_awd_kg: float
    co2e_saved_t: float
    water_saved_pct: float


def run_backtest(days: int = 100, drawdown_cm_day: float = 0.8,
                 rain_series: list[float] | None = None, area_ha: float = 1.0,
                 scaled: bool = False) -> BacktestResult:
    if days <= 0:
        raise ValueError("days must be positive")
    if drawdown_cm_day <= 0:
        raise ValueError("drawdown_cm_day must be positive")
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if rain_series is not None and len(rain_series) != days:
        raise ValueError("rain_series length must equal days")
    rain = rain_series or [0.0] * days
    lvl_a = REFILL_CM
    lvl_cf = REFILL_CM
    irr_a = irr_cf = 0
    wa = wc = 0.0
    fl_a = fl_cf = 0
    for d in range(days):
        stage = stage_on(d)
        trig = trigger_level_cm(stage, scaled)
        lvl_a += rain[d] / 10.0
        lvl_cf += rain[d] / 10.0
        lvl_cf -= drawdown_cm_day
        if lvl_cf < REFILL_CM:
            wc += level_cm_to_m3(REFILL_CM - lvl_cf, area_ha)
            irr_cf += 1
            lvl_cf = REFILL_CM
        lvl_cf = min(lvl_cf, REFILL_CM + 10.0)
        dd_a = drawdown_cm_day if lvl_a >= 0 else 0.5 * drawdown_cm_day
        lvl_a -= dd_a
        if trig is not None and lvl_a <= trig:
            wa += level_cm_to_m3(REFILL_CM - lvl_a, area_ha)
            irr_a += 1
            lvl_a = REFILL_CM
        lvl_a = min(lvl_a, REFILL_CM + 10.0)
        if lvl_a >= 0:
            fl_a += 1
        fl_cf += 1
    sf = effective_sf_w(fl_a, days)
    ch4_cf = seasonal_ch4_kg(days, area_ha, SF_W_CONTINUOUS)
    ch4_a = seasonal_ch4_kg(days, area_ha, sf)
    pct = 100.0 if wc <= 0 else round((1 - wa / wc) * 100, 2)
    return BacktestResult(
        days=days, irrigations_awd=irr_a, irrigations_cf=irr_cf,
        water_awd_m3=round(wa, 1), water_cf_m3=round(wc, 1),
        flooded_days_awd=fl_a, flooded_days_cf=fl_cf, sf_w_eff=round(sf, 4),
        ch4_cf_kg=round(ch4_cf, 2), ch4_awd_kg=round(ch4_a, 2),
        co2e_saved_t=round(co2e_t(ch4_cf - ch4_a), 4),
        water_saved_pct=pct)
