from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# IRIS serves exactly one crop pack (rice) with id|en advisories; the loader
# keeps the PhyToSignal pack-directory structure so more packs can be dropped
# in later without changing call sites.
CROP_PACK_ROOT = Path(__file__).resolve().parents[2] / "crop_packs"
RICE_SLUG = "rice"

DEFAULT_DISCLAIMER = (
    "This result is AI-assisted triage only. It is not a laboratory diagnosis "
    "and should not replace local agricultural expert review."
)


class CropPackService:
    def __init__(self, root: Path = CROP_PACK_ROOT) -> None:
        self.root = root
        self._packs: dict[str, dict[str, Any]] = {}

    def load(self) -> None:
        packs: dict[str, dict[str, Any]] = {}
        for crop_dir in sorted(self.root.iterdir()):
            if not crop_dir.is_dir():
                continue
            crop_pack_path = crop_dir / "crop_pack.json"
            class_mapping_path = crop_dir / "class_mapping.json"
            if not crop_pack_path.exists() or not class_mapping_path.exists():
                continue
            crop_pack = self._read_json(crop_pack_path)
            class_mapping = self._read_json(class_mapping_path)
            classes = [
                class_mapping[key]
                for key in sorted(class_mapping.keys(), key=lambda value: int(value))
            ]
            advisory = {
                "id": self._read_json(crop_dir / "advisory.id.json"),
                "en": self._read_json(crop_dir / "advisory.en.json"),
            }
            risk_rules = self._read_json(crop_dir / "risk_rules.json")
            metadata = self._read_json(crop_dir / "metadata.json")
            demo_samples = self._read_json(crop_dir / "demo_samples.json")
            model_classes_path = crop_dir / "model_classes.json"
            model_classes = self._read_json(model_classes_path) if model_classes_path.exists() else None
            model_path = crop_dir / crop_pack["model_path"]
            supported_model_classes = set(model_classes or []) if model_path.exists() else set()
            if model_path.exists() and not model_classes:
                supported_model_classes = {item["class_slug"] for item in classes}
            classes = [
                {
                    **item,
                    "model_supported": item["class_slug"] in supported_model_classes,
                }
                for item in classes
            ]
            if not model_path.exists():
                model_maturity = "model_pending"
            elif supported_model_classes and len(supported_model_classes) < len(classes):
                model_maturity = "partial_model"
            else:
                model_maturity = "model_backed"
            packs[crop_pack["slug"]] = {
                **crop_pack,
                "path": crop_dir,
                "classes": classes,
                "class_mapping": class_mapping,
                "advisory": advisory,
                "risk_rules": risk_rules,
                "metadata": metadata,
                "demo_samples": demo_samples,
                "model_classes": model_classes,
                "model_maturity": crop_pack.get("model_maturity", model_maturity),
            }
        self._packs = packs

    def all_active(self) -> list[dict[str, Any]]:
        return [pack for pack in self._packs.values() if pack["status"] == "active"]

    def get(self, crop_slug: str = RICE_SLUG) -> dict[str, Any]:
        try:
            return self._packs[crop_slug]
        except KeyError as exc:
            raise KeyError(f"Unsupported crop pack: {crop_slug}") from exc

    def get_class_by_slug(self, crop_slug: str, class_slug: str) -> dict[str, Any]:
        pack = self.get(crop_slug)
        for disease_class in pack["classes"]:
            if disease_class["class_slug"] == class_slug:
                return disease_class
        raise KeyError(f"Unknown class {class_slug} for crop {crop_slug}")

    def get_class_by_index(self, crop_slug: str, index: int) -> dict[str, Any]:
        pack = self.get(crop_slug)
        return pack["class_mapping"][str(index)]

    def get_model_class_by_index(self, crop_slug: str, index: int) -> dict[str, Any]:
        pack = self.get(crop_slug)
        model_classes = pack.get("model_classes")
        if model_classes:
            return self.get_class_by_slug(crop_slug, model_classes[index])
        return self.get_class_by_index(crop_slug, index)

    def class_index(self, crop_slug: str, class_slug: str) -> int:
        pack = self.get(crop_slug)
        for index, disease_class in pack["class_mapping"].items():
            if disease_class["class_slug"] == class_slug:
                return int(index)
        raise KeyError(f"Unknown class {class_slug} for crop {crop_slug}")

    def advisory_for(self, crop_slug: str, class_slug: str, language: str) -> dict[str, Any]:
        language = "en" if language == "en" else "id"
        entries = self.get(crop_slug)["advisory"].get(language, [])
        for entry in entries:
            if entry["class_slug"] == class_slug:
                return entry
        disease_class = self.get_class_by_slug(crop_slug, class_slug)
        return {
            "class_slug": class_slug,
            "disease_name_en": disease_class["name_en"],
            "disease_name_id": disease_class["name_id"],
            "summary": "The image shows a plant health signal that needs cautious review.",
            "visual_signs": ["Visible symptoms may overlap with other stress factors."],
            "immediate_steps": ["Take additional photos under better lighting."],
            "prevention": ["Monitor nearby plants and keep field records."],
            "expert_review_triggers": ["Ask a local agricultural expert if symptoms spread."],
            "disclaimer": DEFAULT_DISCLAIMER,
        }

    def risk_rule_for(self, crop_slug: str, class_slug: str) -> dict[str, Any]:
        for rule in self.get(crop_slug)["risk_rules"]:
            if rule["class_slug"] == class_slug:
                return rule
        disease_class = self.get_class_by_slug(crop_slug, class_slug)
        return {
            "class_slug": class_slug,
            "risk_weight": disease_class["risk_weight"],
            "default_expert_review": disease_class["risk_weight"] >= 0.8,
            "high_risk_conditions": ["multiple reports in same area"],
            "monitoring_priority": "medium",
        }

    def model_path(self, crop_slug: str) -> Path:
        pack = self.get(crop_slug)
        return pack["path"] / pack["model_path"]

    def metadata(self, crop_slug: str) -> dict[str, Any]:
        return self.get(crop_slug)["metadata"]

    @staticmethod
    def class_display_name(disease_class: dict[str, Any], language: str) -> str:
        return disease_class["name_en"] if language == "en" else disease_class["name_id"]

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
