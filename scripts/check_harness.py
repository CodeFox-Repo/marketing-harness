#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REQUIRED_FILES = [
    "pyproject.toml",
    "workspace/portfolios/codefox/portfolio.meta.yaml",
    "workspace/products/codefox/codefox/brand.lock.yaml",
    "workspace/products/codefox/codefox/brand.meta.yaml",
    "workspace/products/codefox/codefox/campaigns/example.campaign.yaml",
    "src/cli.py",
    "src/harness/config.py",
    "src/harness/render.py",
    "src/harness/publish.py",
    "src/harness/style.py",
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    uv_path = shutil.which("uv")
    venv_harness = root / ".venv" / "bin" / "harness"
    harness_entrypoint = (
        "uv run harness"
        if uv_path
        else str(venv_harness)
        if venv_harness.exists()
        else None
    )
    status = {
        "root": str(root),
        "missing": missing,
        "uv_available": uv_path is not None,
        "uv_path": uv_path,
        "venv_harness_available": venv_harness.exists(),
        "harness_entrypoint": harness_entrypoint,
        "env_exists": (root / ".env").exists(),
        "outputs_exists": (root / "outputs").exists(),
        "published_exists": (root / "published").exists(),
        "skill_dir": str(Path(__file__).resolve().parents[1]),
    }
    print(json.dumps(status, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
