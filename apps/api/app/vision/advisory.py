from __future__ import annotations

from typing import Any

from app.vision.crop_packs import DEFAULT_DISCLAIMER, RICE_SLUG, CropPackService


class AdvisoryService:
    def __init__(self, crop_packs: CropPackService) -> None:
        self.crop_packs = crop_packs

    def build(self, crop_slug: str, class_slug: str, language: str) -> dict[str, Any]:
        language = "en" if language == "en" else "id"
        entry = self.crop_packs.advisory_for(crop_slug, class_slug, language)
        triggers = entry.get("expert_review_triggers", [])
        escalation_note = (
            triggers[0]
            if triggers
            else "Please confirm with a local agricultural expert before making field decisions."
        )
        return {
            "language": language,
            "summary": entry["summary"],
            "visual_signs": entry.get("visual_signs", []),
            "immediate_steps": entry.get("immediate_steps", []),
            "prevention": entry.get("prevention", []),
            "expert_review_triggers": triggers,
            "escalation_note": escalation_note,
            "disclaimer": entry.get("disclaimer", DEFAULT_DISCLAIMER),
        }

    def build_bilingual(self, crop_slug: str, class_slug: str) -> dict[str, dict[str, Any]]:
        """Full advisory dicts for both supported languages (id + en)."""
        return {
            lang: self.build(crop_slug, class_slug, lang)
            for lang in ("id", "en")
        }
