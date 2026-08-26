"""Agent tests with a fully mocked (scripted) LLM client - no network."""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from app import db
from app.assistant import agent


# --- fake OpenAI-compatible client -------------------------------------------

class _Function:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id, name, arguments="{}"):
        self.id = call_id
        self.function = _Function(name, arguments)


class _Message:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class _Response:
    def __init__(self, choice):
        self.choices = [choice]


class FakeClient:
    """Scripted chat.completions client.

    `responder(kwargs) -> _Response` is called once per create(); every call
    is recorded for assertions.
    """

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[dict] = []
        outer = self

        class _Completions:
            @staticmethod
            def create(**kwargs):
                outer.calls.append(kwargs)
                return outer.responder(kwargs)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def _tool_call_response(name, args, call_id="call_1"):
    return _Response(_Choice(_Message(
        content=None,
        tool_calls=[_ToolCall(call_id, name, json.dumps(args))]),
        finish_reason="tool_calls"))


def _text_response(text):
    return _Response(_Choice(_Message(content=text)))


@pytest.fixture
def seeded_db(tmp_path):
    db.init_db(f"sqlite:///{(tmp_path / 'agent.db').as_posix()}")
    now = datetime.now(timezone.utc).isoformat()
    transplant = (date.today() - timedelta(days=30)).isoformat()
    with db.session_scope() as conn:
        pid = db.create_plot(conn, name="Sawah Demo - Salatiga",
                             transplant_date=transplant)
        db.insert_reading(conn, plot_id=pid, ts=now, dist_cm=45.0,
                          level_cm=-15.0, batt_v=3.95)
        db.insert_decision(conn, plot_id=pid, ts=now, stage="veg_awd",
                           level_cm=-15.0, action="IRRIGATE",
                           reason_id="Ambang safe-AWD tercapai", rain72_mm=0.0)
    return pid


MESSAGES = [{"role": "user",
             "content": "Kapan sawah saya perlu diairi? Berapa level airnya?"}]


def test_status_question_triggers_tool_and_grounded_reply(seeded_db):
    def responder(kwargs):
        last = kwargs["messages"][-1]
        if last.get("role") == "tool":
            data = json.loads(last["content"])
            return _text_response(
                f"Level air petak Anda {data['level_cm']:+.1f} cm; "
                f"tindakan: {data['action']}.")
        return _tool_call_response("get_plot_status", {})

    out = agent.chat("s1", MESSAGES, client=FakeClient(responder))
    assert out["mode"] == "live"
    assert len(out["tool_trace"]) >= 1
    assert out["tool_trace"][0]["tool"] == "get_plot_status"
    assert set(out["tool_trace"][0].keys()) == {"tool", "args_summary", "ms"}
    assert "-15.0" in out["reply"]
    assert "IRRIGATE" in out["reply"]


def test_tool_loop_cap_stops_at_six_and_answers(seeded_db):
    def responder(kwargs):
        if kwargs.get("tools"):
            return _tool_call_response("get_weather", {})
        return _text_response("Prakiraaan sudah dirangkum di atas.")

    client = FakeClient(responder)
    out = agent.chat("s2", MESSAGES, client=client)
    assert out["mode"] == "live"
    assert len(out["tool_trace"]) == agent.MAX_TOOL_HOPS
    assert all(h["tool"] == "get_weather" for h in out["tool_trace"])
    assert out["reply"] == "Prakiraaan sudah dirangkum di atas."
    assert len(client.calls) == agent.MAX_TOOL_HOPS + 1  # 6 hops + final no-tools


def test_agent_persists_chat_messages(seeded_db):
    def responder(kwargs):
        if kwargs.get("tools") and len([
                m for m in kwargs["messages"] if m.get("role") == "tool"]) == 0:
            return _tool_call_response("search_kb",
                                       {"query": "safe awd"})
        return _text_response("[Sumber: awd-dasar.md] AWD menghemat air.")

    out = agent.chat("sess-persist", MESSAGES, client=FakeClient(responder))
    assert out["mode"] == "live"
    with db.session_scope() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ?"
            " ORDER BY id ASC", ("sess-persist",)).fetchall()
    roles = [r["role"] for r in rows]
    assert roles.count("user") == 1
    assert roles[-1] == "assistant"
    trace_row = rows[-1]
    stored = conn_trace = None
    with db.session_scope() as c2:
        stored = c2.execute(
            "SELECT tool_trace_json FROM chat_messages WHERE session_id = ?"
            " AND role = 'assistant'", ("sess-persist",)).fetchone()
    parsed = json.loads(stored["tool_trace_json"])
    assert parsed[0]["tool"] == "search_kb"


def test_live_reply_strips_markdown_and_source_tags(seeded_db):
    def responder(kwargs):
        return _text_response(
            "**Hold** irrigation.\n\n\n[Source: awd-dasar.md]\n`WAIT`")

    out = agent.chat("s-md", MESSAGES, client=FakeClient(responder))
    assert "**" not in out["reply"]
    assert "`" not in out["reply"]
    assert "[Source:" not in out["reply"]
    assert "Hold irrigation" in out["reply"]
    assert "WAIT" in out["reply"]


def test_live_reply_strips_onnx_jargon(seeded_db):
    def responder(kwargs):
        return _text_response(
            "The ONNX triage classified this leaf as brown spot.")

    out = agent.chat("s-onnx", MESSAGES, client=FakeClient(responder))
    assert "ONNX" not in out["reply"]
    assert "brown spot" in out["reply"]


def test_unknown_image_ref_stays_text_note(seeded_db):
    seen = {}

    def responder(kwargs):
        seen.setdefault("user_msg", kwargs["messages"][1])
        return _text_response("Photo noted.")

    msgs = [{"role": "user", "content": "What is on this leaf?",
             "image_ref": "img_abc123"}]
    out = agent.chat("s3", msgs, client=FakeClient(responder))
    assert out["mode"] == "live"
    assert "img_abc123" in seen["user_msg"]["content"]


def test_registered_image_sent_as_image_url(seeded_db):
    from app.assistant import tools

    ref = tools.register_image_ref(b"\x89PNG\r\n\x1a\n" + b"fake")
    seen = {}

    def responder(kwargs):
        seen["user_msg"] = kwargs["messages"][1]
        return _text_response("ok")

    out = agent.chat("s4", [{"role": "user", "content": "check leaf",
                             "image_ref": ref}], client=FakeClient(responder))
    assert out["mode"] == "live"
    content = seen["user_msg"]["content"]
    assert isinstance(content, list)
    url = next(p["image_url"]["url"] for p in content if p["type"] == "image_url")
    assert url.startswith("data:image/png;base64,")
    assert any("run_vision_triage" in p.get("text", "") for p in content
               if p.get("type") == "text")
