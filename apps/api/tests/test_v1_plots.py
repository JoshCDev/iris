from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


def test_v1_plots_lists_demo_plot(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    with db.session_scope() as conn:
        db.create_plot(conn, name="Sawah Demo - Salatiga",
                       transplant_date="2026-01-01", is_demo=True)
    body = client.get("/api/v1/plots").json()
    assert any(p["name"] == "Sawah Demo - Salatiga" and p["is_demo"]
               for p in body["plots"])


def test_v1_health_ready_has_no_secrets():
    body = client.get("/api/v1/health/ready").json()
    assert body["status"] in ("ok", "degraded")
    assert body["db"] in ("ok", "error")
    assert "onnx" not in body and "llm" not in body
