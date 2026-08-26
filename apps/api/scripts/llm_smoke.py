"""Live LLM smoke (optional): one DeepSeek call with the get_weather tool.

Runs only when DEEPSEEK_API_KEY is set in the environment; otherwise prints
SKIP and exits 0 so CI/demo pipelines never fail on its absence.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("SKIP: DEEPSEEK_API_KEY not set")
        return 0

    from openai import OpenAI

    from app.assistant.prompts import SYSTEM_PROMPT
    from app.assistant.tools import TOOLS, dispatch
    from app.config import get_settings

    settings = get_settings()
    client = OpenAI(base_url="https://api.deepseek.com", api_key=api_key,
                    timeout=30.0, max_retries=1)

    started = time.perf_counter()
    resp = client.chat.completions.create(
        model=settings.iris_llm_model,
        messages=[
            {"role": "system",
             "content": SYSTEM_PROMPT + "\nPanggil tool cuaca sebelum jawab."},
            {"role": "user",
             "content": "Bagaimana prakiraan hujan 72 jam ke depan?"},
        ],
        tools=TOOLS,
    )
    elapsed_s = round(time.perf_counter() - started, 2)
    choice = resp.choices[0]
    msg = choice.message
    tool_calls = [
        {"name": tc.function.name, "arguments": tc.function.arguments}
        for tc in (getattr(msg, "tool_calls", None) or [])
    ]
    trace: list[dict] = []
    if tool_calls:
        messages = [
            {"role": "system",
             "content": SYSTEM_PROMPT + "\nPanggil tool cuaca sebelum jawab."},
            {"role": "user",
             "content": "Bagaimana prakiraan hujan 72 jam ke depan?"},
            {"role": "assistant", "content": msg.content or "",
             "tool_calls": [
                 {"id": tc.id, "type": "function",
                  "function": {"name": tc.function.name,
                               "arguments": tc.function.arguments}}
                 for tc in (msg.tool_calls or [])]},
        ]
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            out, ms = dispatch(tc.function.name, args)
            trace.append({"tool": tc.function.name,
                          "args_summary": json.dumps(args, sort_keys=True)[:120],
                          "ms": ms})
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(out, ensure_ascii=False,
                                                   default=str)})
        final = client.chat.completions.create(
            model=settings.iris_llm_model, messages=messages)
        reply = final.choices[0].message.content or ""
    else:
        reply = msg.content or ""

    print(json.dumps({
        "model": resp.model,
        "finish_reason": choice.finish_reason,
        "first_call_s": elapsed_s,
        "tool_calls": tool_calls,
        "tool_trace": trace,
        "reply_excerpt": reply[:300],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
