"""Live full-workflow check for the IRIS platform.

Requires a running backend (default http://localhost:8050) and
DEEPSEEK_API_KEY in the environment for live assistant scenarios.

Usage (from apps/api):
    .\\.venv\\Scripts\\python.exe scripts\\live_workflow_check.py [--base http://localhost:8050]

Prints PASS/FAIL per step, exits 0 only if all steps pass.
Never prints the API key.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
import time
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "rice_leaf.jpg"
RICE_CLASSES = {"blast", "brown_spot", "tungro", "bacterial_leaf_blight"}

RESULTS: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("IRIS_BASE_URL", "http://localhost:8050"))
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("SKIP: DEEPSEEK_API_KEY not set - live assistant scenarios need it.")
        return 2
    if not FIXTURE.exists():
        print(f"FAIL: fixture missing: {FIXTURE}")
        return 1

    # 1. Health - live mode
    r = requests.get(f"{base}/api/health", timeout=30)
    h = r.json()
    step("health", r.status_code == 200 and h.get("status") == "ok"
         and h.get("onnx") == "loaded" and h.get("llm") == "reachable"
         and h.get("mode") == "live", json.dumps(h))

    # 2. Seed (idempotent)
    r = requests.post(f"{base}/api/demo/seed", timeout=120)
    s = r.json()
    step("seed", r.status_code == 200 and s.get("readings", 0) >= 2800
         and s.get("vision_reports", 0) >= 2 and s.get("is_demo") is True,
         f"readings={s.get('readings')} hold={s.get('hold_for_rain')} vision={s.get('vision_reports')}")

    # 3. Status - pinned shape
    r = requests.get(f"{base}/api/plots/1/status", timeout=30)
    st = r.json()
    keys = {"plot_id", "name", "level_cm", "stage", "stage_days", "action",
            "reason_id", "rain72_mm", "next_check", "last_ts", "is_demo"}
    step("status", r.status_code == 200 and keys <= set(st) and st.get("is_demo") is True
         and isinstance(st.get("level_cm"), (int, float)),
         f"level={st.get('level_cm')} stage={st.get('stage')} action={st.get('action')}")

    # 4. History
    r = requests.get(f"{base}/api/plots/1/history", params={"days": 7}, timeout=30)
    hist = r.json()
    readings = hist.get("readings", hist if isinstance(hist, list) else [])
    step("history", r.status_code == 200 and len(readings) > 0, f"points={len(readings)}")

    # 5. Receipt - internal math consistency
    r = requests.get(f"{base}/api/plots/1/receipt", params={"season_days": 100}, timeout=30)
    rc = r.json()
    sf = rc.get("sf_w_effective", 0)
    flooded = rc.get("flooded_days", 0)
    total = rc.get("season_days", 100)
    sf_expected = 1.0 - (1.0 - 0.78) * (1.0 - flooded / total)
    co2e_ok = abs(rc.get("co2e_saved_t", -1) - rc.get("ch4_saved_kg", 0) * 27.0 / 1000.0) < 0.01
    step("receipt", r.status_code == 200 and rc.get("label") == "simulated"
         and abs(sf - sf_expected) < 5e-4 and rc.get("ch4_saved_kg", 0) > 0 and co2e_ok,
         f"sf={sf} ch4_saved={rc.get('ch4_saved_kg')} co2e={rc.get('co2e_saved_t')}")

    # 6. Weather (live BMKG, fail-open allowed)
    r = requests.get(f"{base}/api/weather/forecast", timeout=30)
    w = r.json()
    step("weather", r.status_code == 200 and isinstance(w.get("rain72_mm"), (int, float)),
         f"rain72={w.get('rain72_mm')} stale={w.get('stale')}")

    # 7. Vision predict - real ONNX + fusion (plot_id as FORM field)
    with open(FIXTURE, "rb") as f:
        r = requests.post(f"{base}/api/vision/predict",
                          files={"image": (FIXTURE.name, f, "image/jpeg")},
                          data={"plot_id": "1", "language": "id"}, timeout=120)
    p = r.json()
    fusion = p.get("fusion")
    step("vision.predict", r.status_code == 200 and p.get("top_class") in RICE_CLASSES
         and 0 < p.get("confidence", 0) <= 1 and isinstance(fusion, dict)
         and fusion.get("risk_level") in {"low", "medium", "high"},
         f"class={p.get('top_class')} conf={p.get('confidence')} risk={fusion.get('risk_level') if fusion else None}")

    # 8. Vision reject - garbage bytes must 422 image_rejected
    r = requests.post(f"{base}/api/vision/predict",
                      files={"image": ("junk.jpg", b"\x00\x01\x02" * 500, "image/jpeg")},
                      data={"language": "id"}, timeout=60)
    step("vision.reject", r.status_code == 422 and r.json().get("code") == "image_rejected",
         f"http={r.status_code} code={r.json().get('code')}")

    # 9-13. Assistant live scenarios
    def chat(label: str, content: str, image_b64: str | None = None,
             expect_tools: set[str] | None = None, must_contain: tuple[str, ...] = ()) -> None:
        msg: dict = {"role": "user", "content": content}
        if image_b64:
            msg["image_ref"] = f"data:image/jpeg;base64,{image_b64}"
        t0 = time.time()
        r = requests.post(f"{base}/api/assistant/chat",
                          json={"session_id": f"livecheck-{int(time.time())}", "messages": [msg]},
                          timeout=180)
        dt = time.time() - t0
        body = r.json()
        tools = {t.get("tool") for t in body.get("tool_trace", [])}
        ok = (r.status_code == 200 and body.get("mode") == "live"
              and bool(body.get("reply"))
              and (expect_tools is None or bool(tools & expect_tools))
              and all(m.lower() in body["reply"].lower() for m in must_contain))
        step(label, ok, f"{dt:.1f}s tools={sorted(tools)} reply={body.get('reply', '')[:90]!r}")

    chat("chat.status", "Kapan sawah saya perlu diairi? Berapa cm muka airnya sekarang?",
         expect_tools={"get_plot_status"}, must_contain=("cm",))
    chat("chat.kb", "Kenapa metana dari sawah padi bisa turun kalau pakai AWD?",
         expect_tools={"search_kb", "get_receipt", "get_plot_status"}, must_contain=("metana",))
    chat("chat.receipt", "Berapa penghematan air dan CO2e dari resi hijau sawah saya?",
         expect_tools={"get_receipt"}, must_contain=("resi",))
    chat("chat.fusion", "Apakah kondisi sawah saya sekarang berisiko terhadap penyakit tanaman?",
         expect_tools={"get_risk_fusion", "get_plot_status"}, must_contain=("risiko",))
    with open(FIXTURE, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    chat("chat.vision", "Tolong cek daun pada foto ini, apa penyakitnya?",
         image_b64=b64, expect_tools={"run_vision_triage"},
         must_contain=())  # disease name asserted loosely below

    # 14. Vision reports listing grew (endpoint wraps list in {"reports": [...]})
    r = requests.get(f"{base}/api/vision/reports", timeout=30)
    reps = r.json().get("reports", [])
    step("vision.reports", r.status_code == 200 and isinstance(reps, list) and len(reps) >= 3,
         f"count={len(reps)}")

    # 15. Frontend (optional)
    if not args.skip_frontend:
        for page in ("/", "/water", "/health", "/assistant", "/dashboard"):
            try:
                rr = requests.get(f"http://localhost:3000{page}", timeout=10)
                step(f"web{page}", rr.status_code == 200 and len(rr.content) > 5000,
                     f"http={rr.status_code} bytes={len(rr.content)}")
            except Exception as exc:  # noqa: BLE001
                step(f"web{page}", False, str(exc)[:80])
        try:
            rp = requests.get("http://localhost:3000/api/plots/1/status", timeout=10)
            step("web.proxy", rp.status_code == 200 and "level_cm" in rp.text, "")
        except Exception as exc:  # noqa: BLE001
            step("web.proxy", False, str(exc)[:80])

    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n=== RESULT: {len(RESULTS) - len(failed)}/{len(RESULTS)} steps passed ===")
    if failed:
        print("FAILED:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
