"""IPCC Tier-1 rice CH4 accounting.
Constants verified against the official IPCC 2006 Guidelines Vol.4 Ch.5:
daily EF_base 1.30 kg CH4/ha/day (Table 5.11, range 0.80-2.20, Yan et al.
2005) and SF_w continuously flooded / multiple aeration = 1 / 0.78
(Table 5.12; multiple-aeration range 0.62-0.98); GWP100 CH4-non-fossil = 27
per IPCC AR6 WG1 Ch.7 Table 7.SM.7.
"""
from dataclasses import dataclass

EF_BASE_KG_CH4_HA_DAY = 1.3
SF_W_CONTINUOUS = 1.0
SF_W_MULTIPLE_AERATION = 0.78
GWP100_CH4_AR6 = 27.0


@dataclass
class GreenReceipt:
    plot_name: str
    season_days: int
    flooded_days: int
    aerated_days: int
    sf_w_effective: float
    water_baseline_m3: float
    water_actual_m3: float
    water_saved_m3: float
    water_saved_pct: float
    ch4_baseline_kg: float
    ch4_actual_kg: float
    ch4_saved_kg: float
    co2e_saved_t: float
    label: str = "simulated"


def ef_c(sf_w: float = 1.0, sf_p: float = 1.0, sf_o: float = 1.0) -> float:
    return EF_BASE_KG_CH4_HA_DAY * sf_w * sf_p * sf_o


def seasonal_ch4_kg(t_days: int = 100, area_ha: float = 1.0, sf_w: float = 1.0,
                    sf_p: float = 1.0, sf_o: float = 1.0) -> float:
    return ef_c(sf_w, sf_p, sf_o) * t_days * area_ha


def effective_sf_w(flooded_days: int, total_days: int) -> float:
    if total_days <= 0:
        raise ValueError("total_days must be positive")
    frac = min(max(flooded_days / total_days, 0.0), 1.0)
    return SF_W_CONTINUOUS - (SF_W_CONTINUOUS - SF_W_MULTIPLE_AERATION) * (1.0 - frac)


def co2e_t(ch4_kg: float, gwp: float = GWP100_CH4_AR6) -> float:
    return ch4_kg * gwp / 1000.0


def build_receipt(plot_name: str, season_days: int, flooded_days: int,
                  water_baseline_m3: float, water_actual_m3: float,
                  area_ha: float = 1.0, sf_p: float = 1.0, sf_o: float = 1.0,
                  label: str = "simulated") -> GreenReceipt:
    if label not in ("simulated", "measured", "projected"):
        raise ValueError("label must be one of: simulated, measured, projected")
    if season_days <= 0:
        raise ValueError("season_days must be positive")
    if not (0 <= flooded_days <= season_days):
        raise ValueError("flooded_days must be within [0, season_days]")
    if area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if water_baseline_m3 <= 0 or water_actual_m3 < 0:
        raise ValueError("water volumes must be positive baseline / non-negative actual")
    if water_baseline_m3 <= water_actual_m3:
        raise ValueError("baseline water must exceed actual for savings receipt")
    sf = effective_sf_w(flooded_days, season_days)
    base = seasonal_ch4_kg(season_days, area_ha, SF_W_CONTINUOUS, sf_p, sf_o)
    act = seasonal_ch4_kg(season_days, area_ha, sf, sf_p, sf_o)
    saved_water = water_baseline_m3 - water_actual_m3
    pct = round(saved_water / water_baseline_m3 * 100.0, 2)
    return GreenReceipt(
        plot_name=plot_name, season_days=season_days, flooded_days=flooded_days,
        aerated_days=season_days - flooded_days, sf_w_effective=round(sf, 4),
        water_baseline_m3=water_baseline_m3, water_actual_m3=water_actual_m3,
        water_saved_m3=saved_water, water_saved_pct=pct,
        ch4_baseline_kg=round(base, 2), ch4_actual_kg=round(act, 2),
        ch4_saved_kg=round(base - act, 2), co2e_saved_t=round(co2e_t(base - act), 4),
        label=label)
