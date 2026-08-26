"""Offline fallback tests: client raising -> offline mode + KB text /
honest miss; last-plot status one-liner on every reply (miss included);
empty KB index; endpoint contract with no key."""
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config as cfg
from app import db
from app import rag
from app.assistant import agent, fallback
import app.main as main_mod


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'fb.db').as_posix()}")


class ExplodingClient:
    class chat:  # noqa: N801 - mimics client.chat.completions.create
        class completions:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("network down")


def test_client_raising_falls_back_with_kb_text(_tmp_db):
    msgs = [{"role": "user",
             "content": "apa itu safe awd dan kapan sawah harus diairi?"}]
    out = agent.chat("s-off", msgs, client=ExplodingClient())
    assert out["mode"] == "offline"
    assert out["tool_trace"] == []
    assert "AWD" in out["reply"]
    assert "[Source:" not in out["reply"]
    assert fallback.OFFLINE_TAG in out["reply"]
    # last-status one-liner may be absent (no readings) but reply must not crash


def test_offline_retrieval_miss_is_honest(_tmp_db):
    msgs = [{"role": "user", "content": "qqq zzz xyzzy plugh?"}]
    out = agent.chat("s-miss", msgs, client=ExplodingClient())
    assert out["mode"] == "offline"
    assert "outside the IRIS knowledge base" in out["reply"]


def _seed_plot_with_latest_state() -> int:
    ts = datetime.now(timezone.utc).isoformat()
    transplant = (date.today() - timedelta(days=30)).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Sawah Demo - Salatiga",
                             transplant_date=transplant)
        db.insert_reading(conn, plot_id=pid, ts=ts, dist_cm=42.0,
                          level_cm=-12.0, batt_v=3.95)
        db.insert_decision(conn, plot_id=pid, ts=ts, stage="veg_awd",
                           level_cm=-12.0, action="IRRIGATE",
                           reason_id="Ambang safe-AWD tercapai",
                           rain72_mm=0.0)
    return pid


def test_offline_miss_still_includes_last_plot_status(_tmp_db):
    """Retrieval-miss replies must still carry the grounded status line."""
    _seed_plot_with_latest_state()
    msgs = [{"role": "user", "content": "qqq zzz xyzzy plugh?"}]
    out = agent.chat("s-miss-status", msgs, client=ExplodingClient())
    assert out["mode"] == "offline"
    assert "outside the IRIS knowledge base" in out["reply"]
    assert fallback.OFFLINE_TAG in out["reply"]
    assert "Last status for Sawah Demo - Salatiga" in out["reply"]
    assert "-12.0 cm" in out["reply"]
    assert "stage vegetative (AWD)" in out["reply"]
    assert "action irrigation needed" in out["reply"]


def test_offline_hit_also_carries_status_line(_tmp_db):
    _seed_plot_with_latest_state()
    msgs = [{"role": "user",
             "content": "apa itu safe awd dan kapan sawah harus diairi?"}]
    out = agent.chat("s-hit-status", msgs, client=ExplodingClient())
    assert "AWD" in out["reply"]
    assert "[Source:" not in out["reply"]
    assert "Last status" in out["reply"]


def test_status_line_absent_without_any_plot(_tmp_db):
    msgs = [{"role": "user", "content": "qqq zzz xyzzy plugh?"}]
    out = fallback.offline_reply(msgs)
    assert "outside the IRIS knowledge base" in out["reply"]
    assert "Last status" not in out["reply"]


def test_empty_kb_index_reports_empty(tmp_path):
    empty = rag.KBSearch([])
    out = fallback.offline_reply(
        [{"role": "user", "content": "apa itu safe awd?"}],
        kb_search=empty)
    assert out["mode"] == "offline"
    assert "knowledge base is empty" in out["reply"]


def test_offline_persists_messages_and_reply(_tmp_db):
    msgs = [{"role": "user", "content": "jelaskan fase tanam padi"}]
    agent.chat("s-persist2", msgs, client=ExplodingClient())
    with db.session_scope() as conn:
        rows = conn.execute(
            "SELECT role FROM chat_messages WHERE session_id = ?"
            " ORDER BY id ASC", ("s-persist2",)).fetchall()
    roles = [r["role"] for r in rows]
    assert roles == ["user", "assistant"]


# --- endpoint contract (no key configured) ------------------------------------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cfg.reset_settings_cache()
    monkeypatch.setattr(agent, "_build_client", lambda: None)
    main_mod._weather_cache.clear()
    return TestClient(main_mod.app)


def test_chat_endpoint_offline_shape(client):
    r = client.post("/api/assistant/chat", json={
        "session_id": "e1",
        "messages": [{"role": "user",
                      "content": "apa itu safe awd?"}]})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"reply", "tool_trace", "mode"}
    assert body["mode"] == "offline"
    assert body["tool_trace"] == []
    assert "AWD" in body["reply"]
    assert "[Source:" not in body["reply"]


def test_chat_endpoint_rejects_bad_role(client):
    r = client.post("/api/assistant/chat", json={
        "session_id": "e2",
        "messages": [{"role": "system", "content": "x"}]})
    assert r.status_code == 422


def test_chat_endpoint_rejects_invalid_image_ref(client):
    r = client.post("/api/assistant/chat", json={
        "session_id": "e3",
        "messages": [{"role": "user", "content": "cek foto",
                      "image_ref": "@@@not-base64@@@"}]})
    assert r.status_code == 422
