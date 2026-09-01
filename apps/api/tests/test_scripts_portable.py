"""Repository-portability gates for the experiment/utility scripts.

Every path-bearing script must expose --help, fail loudly (non-zero) when a
required input is missing, and never require a developer's personal
directory. Committed outputs must not contain absolute personal paths.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PY = sys.executable

SCRIPTS = [
    REPO / "experiments" / "train_rice_v03.py",
    REPO / "experiments" / "audit_rice_vision.py",
    REPO / "apps" / "api" / "scripts" / "eval_vision_test.py",
    REPO / "apps" / "api" / "scripts" / "fetch_spotcheck_images.py",
    REPO / "apps" / "api" / "scripts" / "extract_bmkg_areas.py",
]

# Scripts whose first required input is enforced by argparse.
REQUIRED_INPUT_CASES = [
    (REPO / "experiments" / "train_rice_v03.py",
     ["prepare"]),
    (REPO / "experiments" / "audit_rice_vision.py", []),
    (REPO / "apps" / "api" / "scripts" / "eval_vision_test.py", []),
    (REPO / "apps" / "api" / "scripts" / "extract_bmkg_areas.py", []),
]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_help_exits_zero(script):
    proc = subprocess.run([PY, str(script), "--help"],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert "usage" in proc.stdout.lower()


@pytest.mark.parametrize("script,extra", REQUIRED_INPUT_CASES,
                         ids=lambda p: p.name if isinstance(p, Path) else "")
def test_missing_required_input_exits_nonzero(script, extra):
    proc = subprocess.run([PY, str(script), *extra],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0


def test_audit_missing_dataset_writes_report_without_failure(tmp_path):
    """A missing dataset root is reported, not crashed on."""
    out = tmp_path / "vision_audit.json"
    proc = subprocess.run(
        [PY, str(REPO / "experiments" / "audit_rice_vision.py"),
         "--dataset-root", str(tmp_path / "missing"),
         "--out", str(out)],
        capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["dataset_exists"] is False


def test_no_personal_absolute_paths_in_tracked_sources():
    """Committed Python sources must not reference developer machines."""
    forbidden = ("C:\\xampp", "C:\\Users", "C:\\htdocs", "/Users/", "/home/")
    offenders: list[str] = []
    for script in SCRIPTS:
        text = script.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                offenders.append(f"{script.name}: {marker}")
    assert offenders == []


def test_path_with_spaces_accepted_by_audit(tmp_path):
    """Directories with spaces must not break the CLI contract."""
    root = tmp_path / "my data sets"
    out = root / "vision_audit.json"
    proc = subprocess.run(
        [PY, str(REPO / "experiments" / "audit_rice_vision.py"),
         "--dataset-root", str(root / "missing"),
         "--out", str(out)],
        capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
