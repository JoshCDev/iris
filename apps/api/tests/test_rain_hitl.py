"""LogReg rain HITL: second opinion vs BMKG; never skips irrigation by itself."""
from app.irrigation.rain_hitl import assess_rain_hitl, sigmoid


# Hand-set weights so tests do not depend on the fitted archive file:
# p = sigmoid(bias + w1*rain_1d + w3*rain_3d)
_W = (-0.3, 0.15, 0.08, 0.0, 0.0)


def test_sigmoid_midpoint():
    assert sigmoid(0.0) == 0.5


def test_disagreement_flags_human_review():
    # BMKG says wet (>=15 mm); persistence model sees a dry recent window.
    hitl = assess_rain_hitl(
        bmkg_rain72_mm=20.0, recent_1d_mm=0.0, recent_3d_mm=0.0,
        doy=1, weights=_W)
    assert hitl.bmkg_wet is True
    assert hitl.logreg_wet is False
    assert hitl.needs_review is True
    assert hitl.logreg_p_wet < 0.5


def test_agreement_wet_does_not_need_review():
    hitl = assess_rain_hitl(
        bmkg_rain72_mm=40.0, recent_1d_mm=20.0, recent_3d_mm=40.0,
        doy=1, weights=_W)
    assert hitl.bmkg_wet is True
    assert hitl.logreg_wet is True
    assert hitl.needs_review is False


def test_uncertain_probability_flags_review_even_if_labels_match():
    # logit ~ 0 so p ~ 0.5, inside the uncertain band.
    hitl = assess_rain_hitl(
        bmkg_rain72_mm=0.0, recent_1d_mm=0.0, recent_3d_mm=0.0,
        doy=1, weights=_W)
    assert hitl.bmkg_wet is False
    assert 0.35 <= hitl.logreg_p_wet <= 0.65
    assert hitl.needs_review is True


def test_hitl_never_changes_bmkg_total():
    hitl = assess_rain_hitl(
        bmkg_rain72_mm=12.3, recent_1d_mm=50.0, recent_3d_mm=80.0,
        doy=1, weights=_W)
    assert hitl.bmkg_rain72_mm == 12.3
    assert hitl.bmkg_wet is False
    # Persistence is wet, BMKG is dry: review, but BMKG remains the scheduler input.
    assert hitl.needs_review is True


def test_weather_payload_keeps_bmkg_total(monkeypatch):
    from app.irrigation.rain_hitl import weather_payload

    monkeypatch.setattr(
        "app.irrigation.rain_hitl.fetch_recent_precip",
        lambda lat=-7.331, lon=110.508: (0.0, 0.0, "doy_only"),
    )
    out = weather_payload(17.5, False)
    assert out["rain72_mm"] == 17.5
    assert out["stale"] is False
    assert "hitl" in out
    assert out["hitl"]["bmkg_rain72_mm"] == 17.5
