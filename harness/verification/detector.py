"""Test runner detector for Python, Node.js, Rust, Go, and generic projects."""

import json
from pathlib import Path
import sys
from typing import Optional


def detect_test_command(workspace_root: str) -> Optional[str]:
    """Inspects the workspace and returns the most appropriate test command."""
    root = Path(workspace_root).resolve()

    # 1. Python Pytest detection
    if (
        (root / "pytest.ini").exists()
        or (root / "pyproject.toml").exists()
        or (root / "setup.cfg").exists()
        or (root / "tests").is_dir()
        or list(root.glob("test_*.py"))
        or list(root.glob("*_test.py"))
    ):
        return f"{sys.executable} -m pytest"

    # 2. Node.js NPM detection
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "scripts" in data and "test" in data["scripts"]:
                    return "npm test"
        except Exception:
            return "npm test"

    # 3. Rust Cargo detection
    if (root / "Cargo.toml").exists():
        return "cargo test"

    # 4. Go detection
    if (root / "go.mod").exists():
        return "go test ./..."

    # 5. Generic Python fallback if .py files exist
    if list(root.glob("*.py")):
        return f"{sys.executable} -m unittest discover"

    return None
