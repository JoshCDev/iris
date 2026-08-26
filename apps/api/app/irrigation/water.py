import math


def cm_to_mm(cm: float) -> float:
    return cm * 10.0


def deficit_mm(level_cm: float, refill_cm: float = 5.0) -> float:
    return max(0.0, refill_cm - level_cm) * 10.0


def level_cm_to_m3(cm: float, area_ha: float) -> float:
    return cm * 100.0 * area_ha


def et0_hargreaves(tmin_c: float, tmax_c: float, tmean_c: float,
                   lat_deg: float, doy: int) -> float:
    if not (-90.0 <= lat_deg <= 90.0):
        raise ValueError("lat_deg must be within [-90, 90]")
    if not (1 <= doy <= 366):
        raise ValueError("doy must be within [1, 366]")
    lat = math.radians(lat_deg)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * doy / 365.0)
    decl = 0.409 * math.sin(2.0 * math.pi * doy / 365.0 - 1.39)
    x = max(-1.0, min(1.0, -math.tan(lat) * math.tan(decl)))
    ws = math.acos(x)
    ra = (24.0 * 60.0 / math.pi) * 0.0820 * dr * (
        ws * math.sin(lat) * math.sin(decl)
        + math.cos(lat) * math.cos(decl) * math.sin(ws))
    ra_mm = ra * 0.408
    tr = max(tmax_c - tmin_c, 0.0)
    et0 = 0.0023 * (tmean_c + 17.8) * tr ** 0.5 * ra_mm
    return round(max(et0, 0.0), 3)
