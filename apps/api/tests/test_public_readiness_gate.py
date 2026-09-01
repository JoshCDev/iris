"""Gate: the public-readiness precheck must pass on the committed tree."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "verify_public_readiness.py"


def test_verify_public_readiness_passes():
    proc = subprocess.run([sys.executable, str(SCRIPT)],
                          cwd=str(REPO), capture_output=True, text=True,
                          timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
