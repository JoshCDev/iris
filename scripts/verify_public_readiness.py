"""Pre-publication readiness check for the IRIS repository.

Stdlib-only. Verifies the tip tree is safe and honest for the public
repository reached by the poster QR code:

- no submission-only or obsolete artifacts tracked (poster handoff,
  competition guides, local audit outputs, .env, databases, uploads, ZIPs);
- no personal absolute paths in tracked text sources;
- required public files exist (docs, evidence charts, context CSV);
- the committed E3 backtest matches the pinned README numbers;
- README references [R1]..[R14] are each defined exactly once;
- the ONNX weight hash matches the model card.

Usage:  python scripts/verify_public_readiness.py
Exit 0 when every check passes; 1 otherwise, with [PASS]/[FAIL] lines.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FORBIDDEN_TRACKED = [
    "docs/poster-content.md",
    "docs/competition/",
    "experiments/outputs/vision_audit.json",
    ".env",
    "apps/api/storage/iris.db",
    "apps/api/storage/uploads/",
]

REQUIRED_FILES = [
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "apps/api/crop_packs/rice/model.onnx",
    "assets/poster/chart_results.png",
    "assets/poster/chart_results.svg",
    "assets/poster/chart_water_trace.png",
    "assets/poster/chart_water_trace.svg",
    "experiments/outputs/backtest_summary.json",
    "experiments/outputs/chart_context_data.csv",
]

PERSONAL_PATH_MARKERS = ("C:\\", "c:\\", "/Users/", "/home/")

# Pinned E3 values (README "E3 simulation results" table).
E3_EXPECTED = {
    ("continuous_flooding", "water_m3_ha_season"): 8000.0,
    ("iris_e3", "water_m3_ha_season"): 5000.0,
    ("continuous_flooding", "ch4_kg_ha_season"): 130.0,
    ("iris_e3", "ch4_kg_ha_season"): 115.99,
    ("iris_e3", "ch4_only_avoided_co2e_t_ha_season"): 0.3784,
    ("iris_e3", "effective_sf_w"): 0.8922,
    ("iris_e3", "flooded_days"): 51,
}

TEXT_SUFFIXES = {".py", ".md", ".ts", ".tsx", ".json", ".csv", ".txt",
                 ".ini", ".cfg", ".yml", ".yaml", ".example", ".mjs",
                 ".css", ".html", ".sh", ".sql"}

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")


def tracked_files() -> list[str]:
    proc = subprocess.run(["git", "ls-files"], cwd=REPO,
                          capture_output=True, text=True, check=True)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _violates(file: str, rule: str) -> bool:
    if rule.endswith("/"):
        return file.startswith(rule)
    return file == rule  # exact file rules (e.g. ".env" != ".env.example")


def main() -> int:
    files = tracked_files()

    # 1. Forbidden paths absent from the tip tree.
    bad = [f for f in files
           if any(_violates(f, rule) for rule in FORBIDDEN_TRACKED)]
    check(not bad, "no forbidden artifacts tracked"
          + (f" -> {bad[:5]}" if bad else ""))
    check(not any(f.endswith((".zip", ".log")) for f in files),
          "no zip/log bundles tracked")

    # 2. Required public files exist.
    missing = [f for f in REQUIRED_FILES if f not in files]
    check(not missing, "required public files present"
          + (f" -> missing {missing}" if missing else ""))

    # 3. No personal absolute paths in tracked text sources.
    offenders = []
    for f in files:
        if Path(f).suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = (REPO / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for marker in PERSONAL_PATH_MARKERS:
            if marker in text:
                offenders.append(f"{f} contains {marker!r}")
    check(not offenders, "no personal absolute paths in tracked sources"
          + (f" -> {offenders[:5]}" if offenders else ""))

    # 4. E3 summary schema + pinned values.
    try:
        summary = json.loads(
            (REPO / "experiments" / "outputs" / "backtest_summary.json")
            .read_text(encoding="utf-8"))
        drift = []
        for (section, key), want in E3_EXPECTED.items():
            got = summary.get(section, {}).get(key)
            if got is None or abs(float(got) - want) > 0.005:
                drift.append(f"{section}.{key}: want {want}, got {got}")
        check(not drift, "E3 backtest matches pinned README numbers"
              + (f" -> {drift}" if drift else ""))
        labels = summary.get("evidence_labels", {})
        check(labels.get("water") == "simulated"
              and labels.get("ch4") == "modelled",
              "E3 evidence labels present")
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        check(False, f"E3 backtest readable: {exc}")

    # 5. README references R1..R14 defined exactly once.
    try:
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        for n in range(1, 15):
            defined = len(re.findall(rf"\*\*\[R{n}\]\*\*", readme))
            if defined != 1:
                check(False, f"README [{R if False else n}] defined once "
                             f"(found {defined})")
                break
        else:
            check(True, "README references R1..R14 each defined once")
    except OSError as exc:
        check(False, f"README readable: {exc}")

    # 6. ONNX weight hash matches the model card.
    try:
        model = (REPO / "apps/api/crop_packs/rice/model.onnx").read_bytes()
        digest = hashlib.sha256(model).hexdigest()
        card = (REPO / "docs/MODEL_CARD.md").read_text(encoding="utf-8")
        check(digest in card,
              f"model card records the committed ONNX sha256 ({digest[:12]}...)")
    except OSError as exc:
        check(False, f"model/card readable: {exc}")

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed.")
    if failed:
        print("FAILURES:")
        for label in failed:
            print(f"  - {label}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
