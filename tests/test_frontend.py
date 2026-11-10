import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def test_frontend_suite() -> None:
    """Runs the vitest suite (browser crypto parity with backend vectors, ballot rules, UI)."""
    npm = shutil.which("npm")
    if npm is None or not (FRONTEND / "node_modules").is_dir():
        pytest.skip("npm or frontend/node_modules missing; run `npm install` in frontend/")
    result = subprocess.run([npm, "test"], cwd=FRONTEND, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
