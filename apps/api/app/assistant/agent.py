"""DeepSeek tool-calling agent (OpenAI-compatible Chat Completions).

Loop: chat.completions with tools, max 6 tool hops, 60 s per-call timeout
(vision payloads are larger). Every hop appends to tool_trace
[{tool, args_summary, ms}]. Any live-path failure (no key, network, bad
response) falls back to retrieval with mode='offline'.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.assistant.fallback import offline_reply
from app.assistant.policy import check_reply_safety
from app.assistant.prompts import SYSTEM_PROMPT
from app.assistant.reply_text import plain_reply
from app.assistant.tools import TOOLS, args_summary, dispatch, get_image_ref

log = logging.getLogger("iris.assistant")

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MAX_TOOL_HOPS = 6
CALL_TIMEOUT_S = 60.0

# Bound concurrent live model calls to 2 (AST-007). A blocking acquire IS the
# bound: at most two chats run `_run_loop` at once, the rest queue briefly.
# (A non-blocking acquire + 429 would need a fastapi import here and changes
# the pinned {reply, tool_trace, mode} contract; see task 4.4 report.)
_CHAT_SEMAPHORE = threading.Semaphore(2)

# --- cheap LLM liveness probe (GET /models, short timeout, ~60 s cache) -----

PROBE_TIMEOUT_S = 8.0
LLM_PROBE_TTL_S = 60.0
_llm_probe_cache: dict[str, Any] = {"ts": 0.0, "value": None}
_last_fallback_ts: float | None = None


def reset_llm_probe_cache() -> None:
    _llm_probe_cache["ts"] = 0.0
    _llm_probe_cache["value"] = None


def _raw_llm_probe(timeout_s: float = PROBE_TIMEOUT_S) -> str:
    """One-shot reachability check; 'unreachable' when key absent or the API
    does not answer within `timeout_s`. Uses GET /models (no tokens billed)."""
    from app.config import get_settings

    api_key = get_settings().deepseek_api_key
    if not api_key:
        return "unreachable"
    try:
        from openai import OpenAI

        client = OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=api_key,
                        timeout=timeout_s, max_retries=1)
        client.models.list()
        return "reachable"
    except Exception:
        log.info("llm probe failed: unreachable")
        return "unreachable"


def llm_status(force: bool = False) -> str:
    """Cached 'reachable' | 'unreachable' for /api/health."""
    now = time.monotonic()
    cached = _llm_probe_cache["value"]
    if (not force and cached is not None
            and now - _llm_probe_cache["ts"] < LLM_PROBE_TTL_S):
        return str(cached)
    value = _raw_llm_probe()
    _llm_probe_cache["ts"] = now
    _llm_probe_cache["value"] = value
    return value


def mark_fallback_engaged() -> None:
    """Record that the assistant served a reply via offline fallback."""
    global _last_fallback_ts
    _last_fallback_ts = time.monotonic()


def fallback_engaged_recently(window_s: float = LLM_PROBE_TTL_S) -> bool:
    return (_last_fallback_ts is not None
            and time.monotonic() - _last_fallback_ts < window_s)


def _build_client():
    """Return a live OpenAI-compatible client, or None when unconfigured."""
    from app.config import get_settings

    api_key = get_settings().deepseek_api_key
    if not api_key:
        return None
    from openai import OpenAI

    return OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=api_key,
                  timeout=CALL_TIMEOUT_S, max_retries=1)


def _persist(session_id: str, messages: list[dict[str, Any]], reply: str,
             trace: list[dict[str, Any]]) -> None:
    from app import db

    ts = datetime.now(timezone.utc).isoformat()
    try:
        with db.session_scope() as conn:
            for m in messages:
                conn.execute(
                    "INSERT INTO chat_messages (session_id, ts, role,"
                    " content, tool_trace_json) VALUES (?, ?, ?, ?, NULL)",
                    (session_id, ts, m["role"], m["content"]))
            conn.execute(
                "INSERT INTO chat_messages (session_id, ts, role,"
                " content, tool_trace_json) VALUES (?, ?, ?, ?, ?)",
                (session_id, ts, "assistant", reply,
                 json.dumps(trace, ensure_ascii=False)))
    except Exception:
        log.warning("chat_messages persist failed", exc_info=True)


def _guess_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "image/webp"
    if data.startswith(b"GIF8"):
        return "image/gif"
    return "image/jpeg"


def _llm_content(m: dict[str, Any]) -> str | list[dict[str, Any]]:
    """Plain text, or OpenAI-style multimodal parts when a photo is attached.

    DeepSeek Vision accepts images only on user messages
    (api-docs.deepseek.com/guides/vision, 21 Aug 2026).
    """
    text = str(m.get("content") or "")
    image_ref = m.get("image_ref")
    if not image_ref:
        return text
    data = get_image_ref(str(image_ref))
    if not data:
        note = f"[attached photo not available: {image_ref}]"
        return f"{text}\n{note}" if text else note
    b64 = base64.b64encode(data).decode("ascii")
    parts: list[dict[str, Any]] = []
    if text:
        parts.append({"type": "text", "text": text})
    parts.append({
        "type": "image_url",
        "image_url": {
            "url": f"data:{_guess_mime(data)};base64,{b64}",
            "detail": "high",
        },
    })
    parts.append({
        "type": "text",
        "text": (
            f"image_ref={image_ref}. Call run_vision_triage with this "
            "image_ref for the official class. Do not name tools in the "
            "farmer reply."
        ),
    })
    return parts


def _run_loop(client: Any, messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    from app.config import get_settings

    model = get_settings().iris_llm_model
    convo: list[dict[str, Any]] = [{"role": "system",
                                    "content": SYSTEM_PROMPT}]
    for m in messages:
        role = m.get("role", "user")
        if role == "user":
            convo.append({"role": "user", "content": _llm_content(m)})
        else:
            convo.append({"role": role, "content": str(m.get("content") or "")})

    trace: list[dict[str, Any]] = []
    for _hop in range(MAX_TOOL_HOPS):
        resp = client.chat.completions.create(model=model, messages=convo,
                                              tools=TOOLS)
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return (msg.content or ""), trace
        convo.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name,
                              "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            out, ms = dispatch(name, args)
            trace.append({"tool": name, "args_summary": args_summary(args),
                          "ms": ms})
            convo.append({"role": "tool", "tool_call_id": tc.id,
                          "content": json.dumps(out, ensure_ascii=False,
                                                default=str)})
    final = client.chat.completions.create(model=model, messages=convo)
    return (final.choices[0].message.content or ""), trace


def _policy_safe(reply: str) -> str:
    """Replace a policy-violating reply with the standard refusal (LEAF-009,
    AST-003); untouched replies pass through."""
    replacement = check_reply_safety(reply)
    return replacement if replacement is not None else reply


def chat(session_id: str, messages: list[dict[str, Any]],
         client: Any | None = None) -> dict[str, Any]:
    """Entry point: returns pinned {reply, tool_trace, mode}."""
    if client is None:
        client = _build_client()
    if client is None:
        out = offline_reply(messages)
        mark_fallback_engaged()
        out["reply"] = _policy_safe(plain_reply(out["reply"]))
        _persist(session_id, messages, out["reply"], [])
        return out
    try:
        with _CHAT_SEMAPHORE:
            reply, trace = _run_loop(client, messages)
    except Exception as exc:
        log.warning("live LLM path failed (%s); using offline fallback",
                    type(exc).__name__)
        out = offline_reply(messages)
        mark_fallback_engaged()
        out["reply"] = _policy_safe(plain_reply(out["reply"]))
        _persist(session_id, messages, out["reply"], [])
        return out
    reply = _policy_safe(plain_reply(reply))
    _persist(session_id, messages, reply, trace)
    return {"reply": reply, "tool_trace": trace, "mode": "live"}
