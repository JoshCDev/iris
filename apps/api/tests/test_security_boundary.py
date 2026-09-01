"""Public-readiness security boundary (readiness plan sec 25.7).

Covers the fail-closed demo/non-demo contract: strict IRIS_DEMO_MODE
parsing, startup refusal for unconfigured non-demo mode, the 403 matrix on
interactive routes, and the public read-only set that stays open.

Every test that flips the environment restores the ambient (demo) settings
cache afterwards, because request-time guards read the cached Settings.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config as cfg
from app import db
from app import main as main_mod


def _swap_db(tmp_path) -> None:
    db.init_db(f"sqlite:///{(tmp_path / 'boundary.db').as_posix()}")


def _non_demo_client(tmp_path, monkeypatch, token: str = "dev-token"):
    """Client under a *valid* non-demo configuration (token configured)."""
    _swap_db(tmp_path)
    monkeypatch.setenv("IRIS_DEMO_MODE", "0")
    monkeypatch.setenv("IRIS_DEVICE_TOKEN", token)
    cfg.reset_settings_cache()
    return TestClient(main_mod.app)


def _restore(monkeypatch) -> None:
    monkeypatch.undo()
    cfg.reset_settings_cache()


# --- config parsing -------------------------------------------------------------

def test_demo_mode_accepts_documented_values(monkeypatch):
    for raw, expected in (("1", True), ("0", False), ("true", True),
                          ("FALSE", False), ("yes", True), ("no", False)):
        monkeypatch.setenv("IRIS_DEMO_MODE", raw)
        cfg.reset_settings_cache()
        try:
            assert cfg.get_settings().iris_demo_mode is expected
        finally:
            _restore(monkeypatch)


def test_demo_mode_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("IRIS_DEMO_MODE", "maybe")
    cfg.reset_settings_cache()
    try:
        with pytest.raises(ValueError):
            cfg.get_settings()
    finally:
        _restore(monkeypatch)


def test_non_demo_without_token_refuses_startup(tmp_path, monkeypatch):
    _swap_db(tmp_path)
    monkeypatch.setenv("IRIS_DEMO_MODE", "0")
    monkeypatch.setenv("IRIS_DEVICE_TOKEN", "")
    cfg.reset_settings_cache()
    try:
        with pytest.raises(RuntimeError):
            with TestClient(main_mod.app):
                pass
    finally:
        _restore(monkeypatch)


def test_non_demo_without_token_rejects_ingest(tmp_path, monkeypatch):
    _swap_db(tmp_path)
    monkeypatch.setenv("IRIS_DEMO_MODE", "0")
    monkeypatch.setenv("IRIS_DEVICE_TOKEN", "")
    cfg.reset_settings_cache()
    try:
        r = TestClient(main_mod.app).post(
            "/api/ingest", json={"device_plot_name": "A", "dist_cm": 46.0})
        assert r.status_code == 500
        assert r.json()["detail"]["code"] == "non_demo_token_required"
    finally:
        _restore(monkeypatch)


# --- 403 matrix in valid non-demo mode ------------------------------------------

def test_interactive_routes_403_in_non_demo(tmp_path, monkeypatch):
    c = _non_demo_client(tmp_path, monkeypatch)
    try:
        cases = [
            ("get", "/api/plots/1/status", None),
            ("get", "/api/plots/1/history", None),
            ("get", "/api/plots/1/receipt", None),
            ("get", "/api/weather/forecast", None),
            ("patch", "/api/plots/1", {"bmkg_adm4": "33.73.01.1003"}),
            ("get", "/api/v1/plots", None),
            ("get", "/api/v1/plots/1/today", None),
            ("get", "/api/v1/plots/1/water-history", None),
            ("post", "/api/v1/plots/1/water-observations",
             {"level_cm": -5.0, "source": "manual"}),
            ("post", "/api/v1/plots/1/leaf-assessments", None),
            ("get", "/api/vision/reports", None),
            ("post", "/api/assistant/chat",
             {"session_id": "s1",
              "messages": [{"role": "user", "content": "hi"}]}),
        ]
        for method, url, json_body in cases:
            r = c.request(method, url, json=json_body)
            assert r.status_code == 403, (method, url, r.status_code)
            assert (r.json()["detail"]["code"]
                    == "non_demo_user_auth_required"), url
    finally:
        _restore(monkeypatch)


def test_vision_predict_403_in_non_demo(tmp_path, monkeypatch):
    c = _non_demo_client(tmp_path, monkeypatch)
    try:
        r = c.post("/api/vision/predict",
                   files={"image": ("leaf.jpg", b"not-an-image",
                                    "image/jpeg")})
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "non_demo_user_auth_required"
    finally:
        _restore(monkeypatch)


def test_demo_seed_403_in_non_demo(tmp_path, monkeypatch):
    c = _non_demo_client(tmp_path, monkeypatch)
    try:
        r = c.post("/api/demo/seed")
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "demo_mode_required"
    finally:
        _restore(monkeypatch)


# --- public read-only set stays open --------------------------------------------

def test_public_reads_open_in_non_demo(tmp_path, monkeypatch):
    c = _non_demo_client(tmp_path, monkeypatch)
    try:
        assert c.get("/api/health").status_code == 200
        assert c.get("/api/v1/health/ready").status_code == 200
        assert c.get("/api/v1/evidence/e3").status_code == 200
        assert c.get("/api/v1/evidence/vision").status_code == 200
        assert c.get("/api/weather/areas").status_code == 200
    finally:
        _restore(monkeypatch)


# --- device-token contract --------------------------------------------------------

def test_ingest_token_matrix_in_non_demo(tmp_path, monkeypatch):
    c = _non_demo_client(tmp_path, monkeypatch, token="dev-token")
    try:
        missing = c.post("/api/ingest",
                         json={"device_plot_name": "A", "dist_cm": 46.0})
        assert missing.status_code == 401
        wrong = c.post("/api/ingest",
                       json={"device_plot_name": "A", "dist_cm": 46.0},
                       headers={"X-IRIS-Token": "wrong"})
        assert wrong.status_code == 401
        ok = c.post("/api/ingest",
                    json={"device_plot_name": "A", "dist_cm": 46.0},
                    headers={"X-IRIS-Token": "dev-token"})
        assert ok.status_code == 201
    finally:
        _restore(monkeypatch)


def test_ingest_open_in_demo_mode(tmp_path, monkeypatch):
    _swap_db(tmp_path)
    monkeypatch.setenv("IRIS_DEMO_MODE", "1")
    monkeypatch.setenv("IRIS_DEVICE_TOKEN", "")
    cfg.reset_settings_cache()
    try:
        c = TestClient(main_mod.app)
        assert c.post("/api/ingest",
                      json={"device_plot_name": "A", "dist_cm": 46.0}
                      ).status_code == 201
    finally:
        _restore(monkeypatch)
