from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "skills" / "marketing-harness" / "scripts" / "harness.py"
SANDBOX = ROOT / "skills" / "marketing-harness" / "examples" / "sandbox-product"


def run_harness(product_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--metadata",
            "marketing.harness.yaml",
            *args,
        ],
        cwd=product_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_sandbox_product_smoke_runs_in_temp_copy(tmp_path: Path) -> None:
    product = tmp_path / "sandbox-product"
    shutil.copytree(SANDBOX, product)

    check = run_harness(product, "check")
    assert check.returncode == 0, check.stderr

    state = run_harness(product, "state")
    assert state.returncode == 0, state.stderr
    snapshot = json.loads(state.stdout)
    assert snapshot["errors"] == []
    assert Path(snapshot["project"]["root"]) == product.resolve()
    assert any("accepted.yaml" in path for path in snapshot["read_before_production"])

    validate = run_harness(product, "validate")
    assert validate.returncode == 0, validate.stderr

    render = run_harness(product, "render", "--dry-run")
    assert render.returncode == 0, render.stderr

    output_dir = product / ".harness" / "marketing" / "out" / "launch"
    assert (output_dir / "web-banner.svg").is_file()
    assert (output_dir / "manifest.json").is_file()
    assert (output_dir / "run.lock.json").is_file()
