from dataclasses import dataclass

from app.irrigation.protocol import Stage, trigger_level_cm

REFILL_CM = 5.0
RAIN_SKIP_MM = 15.0


@dataclass
class Decision:
    action: str
    reason_id: str
    refill_to_cm: float | None = None


def decide(level_cm: float, stage: Stage, rain72_mm: float) -> Decision:
    trig = trigger_level_cm(stage)
    if trig is None:
        return Decision("DRAIN",
                        "Season complete: the field can be drained for harvest.")
    if level_cm > trig:
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
