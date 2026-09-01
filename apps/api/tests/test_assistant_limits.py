from fastapi.testclient import TestClient

from app import db
from app import main as main_mod
from app.assistant.policy import check_reply_safety


def _client(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'a.db').as_posix()}")
    return TestClient(main_mod.app)


def test_policy_blocks_pesticide_dose():
    assert check_reply_safety("Use 2 ml per liter of fungicide.") is not None
    assert check_reply_safety("Irrigate to +5 cm and check the leaf.") is None


def test_policy_blocks_unsupported_certainty():
    assert check_reply_safety("This will 100% cure the plant.") is not None


def test_chat_rejects_too_many_messages(tmp_path):
    c = _client(tmp_path)
    msgs = [{"role": "user", "content": "x"} for _ in range(41)]
    r = c.post("/api/assistant/chat",
               json={"session_id": "s1", "messages": msgs})
    assert r.status_code == 422


def test_chat_rejects_oversized_message(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/assistant/chat",
               json={"session_id": "s1",
                     "messages": [{"role": "user", "content": "x" * 8001}]})
    assert r.status_code == 422


def test_chat_rejects_bad_session_id(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/assistant/chat",
               json={"session_id": "../etc/passwd",
                     "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 422


def test_chat_rejects_empty_messages(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/assistant/chat",
               json={"session_id": "s1", "messages": []})
    assert r.status_code == 422
