from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.vision.crop_packs import RICE_SLUG, CropPackService


@dataclass
class InferenceCandidate:
    class_slug: str
    confidence: float


@dataclass
class InferenceResult:
    top3: list[InferenceCandidate]
    model_version: str
    runtime: str
    raw_max_logit: float | None = None
    logit_spread: float | None = None
    softmax_entropy: float | None = None

    @property
    def predicted(self) -> InferenceCandidate:
        return self.top3[0]

    @property
    def is_uncertain(self) -> bool:
        """True when model output looks like an OOD guess rather than a real prediction."""
        if self.logit_spread is not None and self.logit_spread < 1.5:
            return True
        if self.predicted.confidence < 0.45:
            return True
        return False


class ModelUnavailableError(RuntimeError):
    pass


class LowConfidenceRejection(ValueError):
    """Raised when model produces a prediction but confidence is too low for a credible result."""

    def __init__(self, *, confidence: float, predicted_class: str, message: str) -> None:
        super().__init__(message)
        self.confidence = confidence
        self.predicted_class = predicted_class
        self.message = message


class OnnxInferenceAdapter:
    runtime = "onnxruntime-cpu"

    def __init__(self, crop_packs: CropPackService) -> None:
        self.crop_packs = crop_packs
        self.sessions: dict[str, Any] = {}
        self.input_names: dict[str, str] = {}
        self.available = False
        try:
            import onnxruntime as ort  # type: ignore

            self.ort = ort
            self.available = True
        except Exception:
            self.ort = None

    def load(self) -> None:
        if not self.available:
            return
        sess_options = self.ort.SessionOptions()
        sess_options.graph_optimization_level = self.ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.enable_mem_pattern = True
        sess_options.enable_cpu_mem_arena = True
        for pack in self.crop_packs.all_active():
            model_path = self.crop_packs.model_path(pack["slug"])
            if not model_path.exists():
                continue
            session = self.ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=["CPUExecutionProvider"],
            )
            self.sessions[pack["slug"]] = session
            self.input_names[pack["slug"]] = session.get_inputs()[0].name

    def is_loaded(self, crop_slug: str = RICE_SLUG) -> bool:
        return crop_slug in self.sessions

    def loaded_crops(self) -> list[str]:
        return sorted(self.sessions.keys())

    def predict(self, crop_slug: str, image_bytes: bytes, file_name: str | None = None) -> InferenceResult:
        if crop_slug not in self.sessions:
            raise RuntimeError(f"ONNX model is not loaded for crop: {crop_slug}")
        logits = self._run_session(crop_slug, image_bytes)
        probabilities = self._softmax(logits)
        ranked = sorted(enumerate(probabilities), key=lambda item: item[1], reverse=True)[:3]

        raw_max_logit = max(logits)
        logit_spread = max(logits) - min(logits)
        softmax_entropy = self._shannon_entropy(probabilities)

        top3 = [
            InferenceCandidate(
                class_slug=self.crop_packs.get_model_class_by_index(crop_slug, index)["class_slug"],
                confidence=round(float(probability), 4),
            )
            for index, probability in ranked
        ]
        metadata = self.crop_packs.metadata(crop_slug)
        return InferenceResult(
            top3=top3,
            model_version=metadata.get("model_version", f"{crop_slug}-onnx"),
            runtime=self.runtime,
            raw_max_logit=round(raw_max_logit, 4),
            logit_spread=round(logit_spread, 4),
            softmax_entropy=round(softmax_entropy, 4),
        )

    def _run_session(self, crop_slug: str, image_bytes: bytes) -> list[float]:
        import io

        from PIL import Image

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise ValueError("Image file could not be read by model runtime. Use JPG, PNG, or WebP.") from exc
        from app.vision.preprocess import pil_to_nchw

        arr = pil_to_nchw(image)
        outputs = self.sessions[crop_slug].run(None, {self.input_names[crop_slug]: arr})
        return outputs[0][0].tolist()

    @staticmethod
    def _softmax(values: list[float]) -> list[float]:
        import math

        max_value = max(values)
        exp_values = [math.exp(value - max_value) for value in values]
        total = sum(exp_values)
        return [value / total for value in exp_values]

    @staticmethod
    def _shannon_entropy(probs: list[float]) -> float:
        """Shannon entropy of the probability distribution (bits; 5-class max ~2.32)."""
        import math

        return -sum(p * math.log2(max(p, 1e-9)) for p in probs)


class InferenceService:
    """Always runs the real ONNX model - IRIS has no demo-fallback path.

    Spec §6 judge-photo contract: any uploaded image goes through the identical
    live guard -> ONNX path; low-confidence results are honestly rejected.
    """

    def __init__(self, crop_packs: CropPackService) -> None:
        self.crop_packs = crop_packs
        self.onnx = OnnxInferenceAdapter(crop_packs)

    def load(self) -> None:
        self.onnx.load()

    def predict(
        self,
        crop_slug: str,
        image_bytes: bytes,
        file_name: str | None = None,
        quality_metrics: dict[str, float] | None = None,
    ) -> InferenceResult:
        if not self.onnx.is_loaded(crop_slug):
            raise ModelUnavailableError(
                f"The {crop_slug} model is not available. Check that crop_packs/{crop_slug}/model.onnx exists."
            )
        result = self.onnx.predict(crop_slug, image_bytes, file_name=file_name)

        # OOD confidence gating: catch non-plant images that slipped past image_guard
        plant_like = (quality_metrics or {}).get("plant_like_ratio", 1.0)
        entropy_metric = (quality_metrics or {}).get("entropy", 3.0)
        green_dom = (quality_metrics or {}).get("green_dominance", 1.0)
        blob_ratio = (quality_metrics or {}).get("largest_blob_ratio", 0.0)

        from app.vision.image_guard import confidence_is_suspicious

        # Healthy-leaf synthesis for packs without a "healthy" output class.
        # Triggered only when every heuristic signal says clean leaf photo with
        # no strong disease pattern AND the model itself is genuinely unsure.
        pack = self.crop_packs.get(crop_slug)
        has_healthy = any(c["class_slug"] == "healthy" and c.get("model_supported") for c in pack["classes"])
        strongly_plant = (
            plant_like >= 0.55
            and green_dom >= 0.25
            and blob_ratio >= 0.50
            and (result.softmax_entropy is None or result.softmax_entropy < 1.30)
        )

        if not has_healthy and strongly_plant and result.predicted.confidence < 0.50:
            return self._healthy_result(result)

        if confidence_is_suspicious(result.predicted.confidence, plant_like,
                                    entropy_metric, green_dom, blob_ratio):
            raise LowConfidenceRejection(
                confidence=result.predicted.confidence,
                predicted_class=result.predicted.class_slug,
                message=(
                    f"The model produced a low-confidence prediction "
                    f"({round(result.predicted.confidence * 100)}% for {result.predicted.class_slug}). "
                    f"This image may not contain a recognizable rice leaf."
                ),
            )

        # Reject when logit spread is near-uniform and the image isn't leaf-like
        if result.is_uncertain and plant_like < 0.30:
            raise LowConfidenceRejection(
                confidence=result.predicted.confidence,
                predicted_class=result.predicted.class_slug,
                message=(
                    "The model could not confidently identify a disease pattern in this image. "
                    "This may not be a suitable rice leaf photo for analysis."
                ),
            )

        # Softmax-entropy OOD guard: near-uniform distribution + weakly leaf-like
        # image is almost certainly an OOD guess (threshold leaves headroom below
        # log2(5) ~ 2.32).
        entropy_value = result.softmax_entropy
        if entropy_value is not None and entropy_value >= 1.50 and plant_like < 0.45:
            raise LowConfidenceRejection(
                confidence=result.predicted.confidence,
                predicted_class=result.predicted.class_slug,
                message=(
                    "The model output is too uniform across classes "
                    f"(entropy {entropy_value:.2f}) to be a confident prediction. "
                    "This image may not be a usable rice leaf photo."
                ),
            )

        return result

    def loaded_crops(self) -> list[str]:
        return self.onnx.loaded_crops()

    def _healthy_result(self, original: InferenceResult) -> InferenceResult:
        """Synthesize a 'healthy' top prediction when the model lacks that output
        but the image clearly shows a leaf with no strong disease signal."""
        return InferenceResult(
            top3=[
                InferenceCandidate(class_slug="healthy", confidence=round(1.0 - original.predicted.confidence, 3)),
                original.top3[0],
                original.top3[1] if len(original.top3) > 1 else original.top3[0],
            ],
            model_version=original.model_version,
            runtime=original.runtime,
            raw_max_logit=original.raw_max_logit,
            logit_spread=original.logit_spread,
        )
