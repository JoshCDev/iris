#!/usr/bin/env python
"""Self-contained end-to-end integration check for the IRIS platform.

Run from apps/api with the repo venv python - NO live servers required:
    ..\\..\\.venv\\Scripts\\python.exe scripts\\e2e_check.py

Everything runs in-process: the demo seeder and service layers are called
directly, HTTP-shaped contracts go through FastAPI's TestClient, and the LLM
is fully mocked (no network, no key needed).

Chain asserted (prints PASS/FAIL per step, exits 0/1):
  1. seed            -> deterministic demo data lands (2880 readings, >=1 HOLD_FOR_RAIN)
  2. status          -> pinned {plot_id..is_demo} response shape
  3. history         -> 2880 readings (+2880 decisions) over the seeded window
  4. receipt         -> IPCC Tier-1 numbers internally consistent
                        (sf_w_eff == 1 - 0.22*(1 - flooded/100);
                         ch4_saved > 0; co2e_t == ch4_saved*27/1000 rounded;
                         label 'simulated')
  5. vision predict  -> real ONNX triage of tests/fixtures/rice_leaf.jpg,
                        top_class in the 4 disease classes, fusion present
                        (plot_id given -> hydrology x weather x disease)
  6. assistant chat  -> MOCKED llm client drives a tool hop; pinned
                        {reply, tool_trace, mode} with mode in {live, offline}
  7. health          -> llm in {reachable, unreachable}, mode in {live, offline}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Windows consoles often default to cp1252; force UTF-8 so Unicode output
# (plot names, arrows) never crashes the report.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FIXTURE = API_DIR / "tests" / "fixtures" / "rice_leaf.jpg"
PINNED_STATUS_KEYS = {"plot_id", "name", "level_cm", "stage", "stage_days",
                      "action", "reason_id", "rain72_mm", "next_check",
                      "last_ts", "is_demo"}
PINNED_VISION_KEYS = {"report_id", "top_class", "class_label_id",
                      "class_label_en", "confidence", "severity",
                      "advisory_id", "advisory_en", "fusion", "is_demo"}
MODEL_CLASSES = {"bacterial_leaf_blight", "blast", "brown_spot", "tungro"}
GWP_CH4_AR6 = 27.0

_results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    _results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def step(fn: Callable[[], str]) -> Callable[[], None]:
    def wrapper() -> None:
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - report any failure inline
            record(fn.__name__.removeprefix("step_"), False,
                   f"{type(exc).__name__}: {exc}")
            return
        record(fn.__name__.removeprefix("step_"), True, detail)
    wrapper.__name__ = fn.__name__
    return wrapper


# --- mocked OpenAI-compatible client (scripted single tool hop) --------------

class _Function:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.function = _Function(name, arguments)


class _Message:
    def __init__(self, content: str | None, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, message: _Message) -> None:
        self.message = message


class _Response:
    def __init__(self, choice: _Choice) -> None:
        self.choices = [choice]


class FakeLLMClient:
    """Calls get_plot_status once, then answers from the tool output."""

    def __init__(self) -> None:
        outer = self

        class _Completions:
            @staticmethod
            def create(**kwargs: Any) -> _Response:
                last = kwargs["messages"][-1]
                if last.get("role") == "tool":
                    data = json.loads(last["content"])
                    return _Response(_Choice(_Message(
                        f"Level air petak Anda {float(data['level_cm']):+.1f} cm"
                        f" pada fase {data['stage']}; tindakan: "
                        f"{data['action']}.")))
                return _Response(_Choice(_Message(
                    content=None,
                    tool_calls=[_ToolCall("call_e2e_1", "get_plot_status",
                                          "{}")])))

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


# --- steps --------------------------------------------------------------------

_ctx: dict[str, Any] = {}


@step
def step_seed() -> str:
    from scripts.seed_demo import seed_demo

    summary = seed_demo()
    _ctx["plot_id"] = int(summary["plot_id"])
    ok = (summary["readings"] == 2880 and summary["decisions"] == 2880
          and summary["hold_for_rain"] >= 1)
    assert ok, f"unexpected seed summary: {summary}"
    return (f"plot {summary['plot_id']} '{summary['name']}' seeded:"
            f" {summary['readings']} readings, {summary['irrigations']}"
            f" irrigations, {summary['hold_for_rain']} HOLD_FOR_RAIN,"
            f" {summary['vision_reports']} demo vision reports")


@step
def step_status() -> str:
    from fastapi.testclient import TestClient

    import app.main as main_mod

    with TestClient(main_mod.app) as client:
        r = client.get(f"/api/plots/{_ctx['plot_id']}/status")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    body = r.json()
    assert set(body.keys()) == PINNED_STATUS_KEYS, \
        f"shape mismatch: {sorted(body.keys())}"
    assert body["level_cm"] is not None and body["action"] is not None
    assert body["is_demo"] is True
    return (f"pinned shape ok; level_cm={body['level_cm']} "
            f"stage={body['stage']} action={body['action']}")


@step
def step_history() -> str:
    from fastapi.testclient import TestClient

    import app.main as main_mod

    with TestClient(main_mod.app) as client:
        r = client.get(f"/api/plots/{_ctx['plot_id']}/history?days=40")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    body = r.json()
    n_readings, n_decisions = len(body["readings"]), len(body["decisions"])
    assert n_readings == 2880, f"expected 2880 readings, got {n_readings}"
    assert n_decisions == 2880, f"expected 2880 decisions, got {n_decisions}"
    levels = [x["level_cm"] for x in body["readings"]]
    assert min(levels) <= -15.0 and max(levels) >= 0.0, \
        "sawtooth range violated"
    holds = sum(1 for d in body["decisions"]
                if d["action"] == "HOLD_FOR_RAIN")
    assert holds >= 1, "rain-hold story missing from history"
    return (f"{n_readings} readings / {n_decisions} decisions;"
            f" sawtooth {min(levels):+.1f}..{max(levels):+.1f} cm;"
            f" {holds} rain-holds")


@step
def step_receipt() -> str:
    from fastapi.testclient import TestClient

    import app.main as main_mod

    with TestClient(main_mod.app) as client:
        r = client.get(f"/api/plots/{_ctx['plot_id']}/receipt?season_days=100")
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    body = r.json()
    season, flooded = body["season_days"], body["flooded_days"]
    sf_expected = 1.0 - 0.22 * (1.0 - flooded / season)
    sf_diff = abs(body["sf_w_effective"] - sf_expected)
    assert sf_diff <= 5e-5, \
        f"sf_w_eff {body['sf_w_effective']} != {sf_expected:.6f} (diff {sf_diff})"
    assert body["ch4_saved_kg"] > 0, "ch4_saved must be positive"
    co2e_expected = round(body["ch4_saved_kg"] * GWP_CH4_AR6 / 1000.0, 4)
    co2e_diff = abs(body["co2e_saved_t"] - co2e_expected)
    assert co2e_diff <= 1e-3, \
        f"co2e {body['co2e_saved_t']} != {co2e_expected} (diff {co2e_diff})"
    assert body["label"] == "simulated", "honesty rule: receipts simulated"
    assert body["water_saved_m3"] > 0
    return (f"flooded {flooded}/{season} d; sf_w_eff={body['sf_w_effective']};"
            f" water -{body['water_saved_m3']:,.0f} m3"
            f" ({body['water_saved_pct']}%); CH4 -{body['ch4_saved_kg']} kg;"
            f" CO2e -{body['co2e_saved_t']} t [{body['label']}]")


@step
def step_vision_predict() -> str:
    from fastapi.testclient import TestClient

    import app.main as main_mod

    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    with TestClient(main_mod.app) as client:
        with open(FIXTURE, "rb") as fh:
            r = client.post(
                "/api/vision/predict",
                files={"image": ("rice_leaf.jpg", fh, "image/jpeg")},
                data={"plot_id": str(_ctx["plot_id"]), "language": "en"})
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    body = r.json()
    assert set(body.keys()) == PINNED_VISION_KEYS, "vision shape mismatch"
    assert body["top_class"] in MODEL_CLASSES, \
        f"top_class {body['top_class']} outside 4 classes"
    assert 0.0 < body["confidence"] <= 1.0
    fusion = body["fusion"]
    assert fusion is not None, "fusion missing although plot_id was given"
    assert fusion.get("risk_level") in {"low", "medium", "high"}
    assert isinstance(fusion.get("drivers_id"), list) and fusion["drivers_id"]
    assert isinstance(fusion.get("drivers_en"), list) and fusion["drivers_en"]
    return (f"top_class={body['top_class']} conf={body['confidence']}"
            f" severity={body['severity']}; fusion risk={fusion['risk_level']}"
            f" driver='{fusion['drivers_id'][0]}'")


@step
def step_assistant_chat_mocked_llm() -> str:
    from fastapi.testclient import TestClient

    import app.assistant.agent as agent_mod
    import app.main as main_mod

    original = agent_mod._build_client
    agent_mod._build_client = lambda: FakeLLMClient()
    try:
        with TestClient(main_mod.app) as client:
            r = client.post("/api/assistant/chat", json={
                "session_id": "e2e-check",
                "messages": [{"role": "user",
                              "content": "Kapan sawah saya perlu diairi?"}]})
    finally:
        agent_mod._build_client = original
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    body = r.json()
    assert set(body.keys()) == {"reply", "tool_trace", "mode"}, \
        "chat shape mismatch"
    assert body["mode"] in {"live", "offline"}, f"bad mode {body['mode']}"
    assert isinstance(body["tool_trace"], list)
    assert body["mode"] == "live", "mocked client must take the live path"
    assert len(body["tool_trace"]) >= 1, "expected >=1 tool hop"
    assert all(set(h.keys()) == {"tool", "args_summary", "ms"}
               for h in body["tool_trace"])
    assert body["reply"].strip(), "empty reply"
    trace_txt = ", ".join(h["tool"] for h in body["tool_trace"])
    return (f"mode={body['mode']}; hops=[{trace_txt}];"
            f" reply='{body['reply'][:60]}...'")


@step
def step_health() -> str:
    from fastapi.testclient import TestClient

    import app.main as main_mod

    with TestClient(main_mod.app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    body = r.json()
    assert body["llm"] in {"reachable", "unreachable"}, \
        f"llm field invalid: {body['llm']}"
    assert body["mode"] in {"live", "offline"}, \
        f"mode field invalid: {body['mode']}"
    assert body["db"] == "ok" and body["onnx"] in {"loaded", "not_loaded"}
    return (f"status={body['status']} db={body['db']} onnx={body['onnx']}"
            f" llm={body['llm']} mode={body['mode']}")


def main() -> int:
    print("=== IRIS e2e_check (in-process; no live servers needed) ===")
    for sfn in (step_seed, step_status, step_history, step_receipt,
                step_vision_predict, step_assistant_chat_mocked_llm,
                step_health):
        sfn()
    failed = [name for name, ok, _ in _results if not ok]
    passed = len(_results) - len(failed)
    print(f"\n=== RESULT: {passed}/{len(_results)} steps passed ===")
    if failed:
        print(f"FAILED steps: {', '.join(failed)}")
        return 1
    print("ALL GREEN - full chain verified (seed → status → history → "
          "receipt → vision+fusion → assistant(mocked) → health)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
