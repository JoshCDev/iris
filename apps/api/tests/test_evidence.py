from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_e3_evidence_pinned_values_and_labels():
    body = client.get("/api/v1/evidence/e3").json()
    assert body["label"] == "DEFINED SIMULATION"
    assert body["evidence_type"] == "simulated"
    assert body["assumptions"]["season_days"] == 100
    assert body["assumptions"]["area_ha"] == 1.0
    assert body["assumptions"]["rain_mm"] == 0
    assert body["assumptions"]["drawdown_cm_per_day"] == 0.8
    assert body["values"]["water_saved_pct"] == 37.5
    assert body["values"]["water_cf_m3"] == 8000.0
    assert body["values"]["water_awd_m3"] == 5000.0
    assert any("-15 cm" in d for d in body["disclosures"])
    assert body["source_version"] == "backtest_summary.json"


def test_vision_evidence_benchmark_labels():
    body = client.get("/api/v1/evidence/vision").json()
    assert body["label"] == "PUBLIC-DATASET BENCHMARK"
    assert body["n"] == 1621
    assert body["accuracy"] == 0.9784
    assert body["field_validation"] == "pending"
    assert body["model_version"]
