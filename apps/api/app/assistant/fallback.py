"""Offline fallback (mode='offline'): TF-IDF retrieval over the KB.

Used whenever the live LLM path is unavailable (no key, network error, bad
response). The reply is tagged [offline mode] and uses KB text, or honestly
reports a retrieval miss ("outside the IRIS knowledge base"). Every offline
reply also carries a grounded last-plot status one-liner (level, stage, action)
when any plot has readings, so the farmer always gets actionable state.
"""
from __future__ import annotations

from typing import Any

OFFLINE_TAG = "[offline mode] "

# Human-readable labels so the status one-liner never leaks raw stage/action
# slugs (e.g. "veg_awd", "IRRIGATE") into farmer-facing chat text.
_STAGE_LABELS = {
    "establishment": "establishment",
    "veg_awd": "vegetative (AWD)",
    "flowering_lock": "flowering (must flood)",
    "grain_fill_awd": "grain fill (AWD)",
    "harvest": "harvest",
}

_ACTION_LABELS = {
    "WAIT": "wait (safe)",
    "HOLD_FOR_RAIN": "hold irrigation (waiting for rain)",
    "LOWER_POND": "lower pond toward +5 cm if a drain exists (not AWD dry-down)",
    "IRRIGATE": "irrigation needed",
    "DRAIN": "drain the field (harvest)",
}


def _last_status_line() -> str:
    try:
        from app.db import latest_decision, session_scope

        with session_scope() as conn:
            row = conn.execute(
                "SELECT p.id AS id, p.name AS name, r.level_cm AS level_cm,"
                " r.ts AS rts FROM plots p"
                " JOIN readings r ON r.plot_id = p.id"
                " ORDER BY r.ts DESC LIMIT 1").fetchone()
            if row is None:
                return ""
            decision = latest_decision(conn, int(row["id"]))
            action = decision["action"] if decision is not None else "-"
            stage = decision["stage"] if decision is not None else "-"
            stage_lbl = _STAGE_LABELS.get(str(stage), str(stage))
            action_lbl = _ACTION_LABELS.get(str(action), str(action))
            return (f"\nLast status for {row['name']}: "
                    f"{float(row['level_cm']):+.1f} cm, stage {stage_lbl}, "
                    f"action {action_lbl}.")
    except Exception:
        return ""


def offline_reply(messages: list[dict[str, Any]],
                  kb_search: Any | None = None) -> dict[str, Any]:
    """Build an offline answer from KB retrieval (+ last status one-liner).

    The status one-liner is appended to EVERY offline reply (retrieval hits,
    misses, and empty-KB cases alike) whenever a plot with readings exists.
    """
    from app.rag import get_kb_search

    query = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            query = str(m["content"])
            break

    ks = kb_search if kb_search is not None else get_kb_search()
    ans = ks.answer(query)
    parts = [OFFLINE_TAG + ans.text]
    parts.append(_last_status_line())
    return {"reply": "".join(parts), "tool_trace": [], "mode": "offline"}
