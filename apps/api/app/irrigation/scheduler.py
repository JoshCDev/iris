from dataclasses import dataclass

from app.irrigation.protocol import Stage, trigger_level_cm

REFILL_CM = 5.0
RAIN_SKIP_MM = 15.0
# IRRI refill is ~5 cm; standing water of 5–10 cm still leaves the canopy in air.
# At >= 15 cm the pond is already deep vs that protocol (young plants especially).
# Complete canopy submergence of a tillering plant is typically much deeper;
# this is flood relief toward +5 cm, not an AWD dry-down to -15 cm.
EXCESS_POND_CM = 15.0


@dataclass
class Decision:
    action: str
    reason_id: str
    refill_to_cm: float | None = None


def decide(level_cm: float, stage: Stage, rain72_mm: float, *,
           water_fresh: bool = True,
           weather_availability: str = "fresh") -> Decision:
    if not water_fresh:
        return Decision(
            "RECHECK_REQUIRED",
            "Data air kedaluwarsa atau hilang: ukur ulang level pipa dan "
            "periksa kembali dalam 15 menit.")
    if weather_availability == "unavailable":
        return Decision(
            "RECHECK_REQUIRED",
            "Prakiraan BMKG tidak tersedia: saran berbasis hujan tidak "
            "lengkap. Periksa kondisi lokal dan ulangi pengecekan.")
    trig = trigger_level_cm(stage)
    if trig is None:
        return Decision("DRAIN",
                        "Season complete: the field can be drained for harvest.")
    if stage != Stage.HARVEST and level_cm >= EXCESS_POND_CM:
        return Decision(
            "LOWER_POND",
            "Excess pond. If a drain, spillway, or bund cut is available, "
            f"lower the water toward +{REFILL_CM:.0f} cm so leaves stay in air. "
            "Do not dry the field to the AWD trigger. "
            "Evaporation alone is too slow at this depth. "
            "Check again in 15 minutes.",
        )
    if level_cm > trig:
        if stage != Stage.HARVEST and level_cm >= 0.0:
            return Decision(
                "WAIT",
                "Do not drain. The water table is above the AWD band "
                f"({level_cm:+.1f} cm; trigger {trig:+.1f} cm). "
                "Safe AWD waits for the table to fall by itself; "
                "pumping out is not the protocol. Check again in 15 minutes.",
            )
        return Decision("WAIT",
                        f"Safe ({level_cm:+.1f} cm; trigger {trig:+.1f} cm). "
                        "Check again in 15 minutes.")
    hard_floor = trig - 10.0
    if rain72_mm >= RAIN_SKIP_MM and level_cm > hard_floor \
            and stage not in (Stage.FLOWERING_LOCK, Stage.ESTABLISHMENT):
        return Decision("HOLD_FOR_RAIN",
                        f"Holding for rain: {rain72_mm:.0f} mm forecast in 72 h.")
    if stage == Stage.FLOWERING_LOCK:
        return Decision("IRRIGATE",
                        "Flowering lock: keep the field flooded (≥ +3 cm) to protect yield.",
                        refill_to_cm=REFILL_CM)
    return Decision("IRRIGATE",
                    f"Safe-AWD trigger reached ({level_cm:+.1f} cm). "
                    f"Irrigate to +{REFILL_CM:.0f} cm.",
                    refill_to_cm=REFILL_CM)
