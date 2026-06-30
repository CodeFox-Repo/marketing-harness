from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVE = ROOT / "tests" / "sandbox" / "drive.py"


def test_sandbox_drive_full_lifecycle() -> None:
    # Exercises validate -> dry-run render -> stub produce -> settle (image +
    # multimodal copy) -> report. This is the only coverage of the produce+settle
    # loop; dry-run alone never reaches settle.
    result = subprocess.run(
        [sys.executable, str(DRIVE)], capture_output=True, text=True
    )
    assert result.returncode == 0, f"sandbox drive failed:\n{result.stdout}\n{result.stderr}"
    assert "PASS:" in result.stdout


SANDBOX_KOBE = ROOT / "tests" / "sandbox-kobe"
STUDIO = ROOT / "skills" / "brand-studio" / "scripts" / "studio.py"


def _studio(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(STUDIO), "--project-root", str(SANDBOX_KOBE),
         "--metadata", "marketing.studio.yaml", *args],
        cwd=SANDBOX_KOBE, capture_output=True, text=True,
    )


def test_kobe_sandbox_validates_and_renders() -> None:
    # Real kobe brand corpus migrated to the new studio layout; dogfoods the
    # runtime against an actual product theme + campaign.
    validate = _studio(["repo", "validate"])
    assert validate.returncode == 0, validate.stderr
    assert "theme 'kobe'" in validate.stdout
    render = _studio(["repo", "render", "--dry-run"])
    assert render.returncode == 0, render.stderr


def test_repo_init_writes_validate_ready_revision(tmp_path) -> None:
    # Regression: `repo init` must write a positive revision so a freshly
    # initialized repo passes `repo validate` (previously wrote 0 -> rejected).
    import importlib.util
    spec = importlib.util.spec_from_file_location("studio_revcheck", STUDIO)
    assert spec is not None and spec.loader is not None
    studio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(studio)
    plan = studio.project_paths({}, tmp_path)
    for directory in (plan["asset_index"].parent, plan["accepted_state"].parent):
        directory.mkdir(parents=True, exist_ok=True)
    for portfolio in plan["portfolios"].values():
        portfolio["accepted"].parent.mkdir(parents=True, exist_ok=True)
    studio.write_initial_state_files(plan, tmp_path, {})
    data = studio.read_yaml_mapping(plan["accepted_state"])
    assert data["revision"] >= 1
