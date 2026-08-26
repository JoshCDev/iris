from __future__ import annotations


def severity_label(score: int) -> str:
    if score <= 25:
        return "Low"
    if score <= 50:
        return "Moderate"
    if score <= 75:
        return "High"
    return "Urgent Review"


def calculate_severity(
    *,
    class_slug: str,
    confidence: float,
    risk_weight: float,
    recent_same_area_count: int = 0,
    default_expert_review: bool = False,
) -> tuple[int, str, bool]:
    if class_slug == "healthy":
        score = min(25, round(confidence * 20))
        return score, "Low", False

    base = confidence * 50
    risk = risk_weight * 35
    context = min(15, max(0, recent_same_area_count) * 3)
    score = min(100, round(base + risk + context))
    label = severity_label(score)
    needs_review = (
        confidence < 0.65
        or default_expert_review
        or score >= 51
        or (risk_weight >= 0.8 and confidence >= 0.55)
    )
    return score, label, needs_review
