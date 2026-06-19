from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "skills" / "marketing-harness" / "scripts" / "harness.py"


def load_launcher() -> ModuleType:
    spec = importlib.util.spec_from_file_location("marketing_harness_skill_launcher", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata(root: Path) -> dict[str, object]:
    return {
        "project": {
            "root": str(root),
            "marketingRoot": "packages/branding/marketing",
        },
        "brand": {
            "lock": "packages/branding/marketing/brand.lock.yaml",
            "campaigns": "packages/branding/marketing/campaigns",
            "references": "packages/branding/marketing/references",
        },
        "campaign": {
            "name": "launch",
            "path": "packages/branding/marketing/campaigns/launch.campaign.yaml",
        },
        "artifacts": {
            "scratch": "packages/branding/.harness/out",
            "approved": "packages/branding/public/marketing",
        },
        "state": {
            "plans": "packages/branding/marketing/plans",
            "accepted": "packages/branding/marketing/accepted.yaml",
        },
    }


def test_metadata_supplies_validate_and_render_paths(tmp_path: Path) -> None:
    launcher = load_launcher()
    meta = metadata(tmp_path)

    validate_args = launcher.apply_metadata_args(["validate"], meta)
    render_args = launcher.apply_metadata_args(["render", "--dry-run"], meta)

    campaign = str(tmp_path / "packages/branding/marketing/campaigns/launch.campaign.yaml")
    brand = str(tmp_path / "packages/branding/marketing/brand.lock.yaml")
    outputs = str(tmp_path / "packages/branding/.harness/out")
    assert validate_args == ["validate", campaign, "--brand", brand]
    assert render_args == [
        "render",
        campaign,
        "--dry-run",
        "--brand",
        brand,
        "--outputs-dir",
        outputs,
    ]


def test_metadata_project_paths_are_root_relative(tmp_path: Path) -> None:
    launcher = load_launcher()

    paths = launcher.project_paths(metadata(tmp_path), tmp_path)

    assert paths["marketing_root"] == tmp_path / "packages/branding/marketing"
    assert paths["campaigns_dir"] == tmp_path / "packages/branding/marketing/campaigns"
    assert paths["references_dir"] == tmp_path / "packages/branding/marketing/references"
    assert paths["plans_dir"] == tmp_path / "packages/branding/marketing/plans"
    assert paths["accepted_state"] == tmp_path / "packages/branding/marketing/accepted.yaml"


def test_launcher_resolves_to_bundled_cli() -> None:
    launcher = load_launcher()

    assert launcher.bundled_cli_command() == [
        sys.executable,
        str(ROOT / "skills/marketing-harness/scripts/cli.py"),
    ]


def test_bootstrap_is_dry_run_until_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = load_launcher()
    meta = metadata(tmp_path)
    marketing_root = tmp_path / "packages/branding/marketing"
    plans = tmp_path / "packages/branding/marketing/plans"
    accepted_parent = tmp_path / "packages/branding/marketing"
    scratch = tmp_path / "packages/branding/.harness/out"

    assert launcher.bootstrap_project([str(tmp_path)], meta, "marketing.harness.yaml") == 0
    assert not marketing_root.exists()
    assert not scratch.exists()
    assert "mode=dry-run" in capsys.readouterr().out

    assert (
        launcher.bootstrap_project(["--write", str(tmp_path)], meta, "marketing.harness.yaml")
        == 0
    )
    assert marketing_root.is_dir()
    assert plans.is_dir()
    assert accepted_parent.is_dir()
    assert scratch.is_dir()
    assert "mode=write" in capsys.readouterr().out


def test_publish_is_not_a_user_facing_command() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "skills/marketing-harness/scripts/cli.py"), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "publish" not in completed.stdout


def test_render_dry_run_uses_bundled_scripts(tmp_path: Path) -> None:
    project = tmp_path
    brand = project / "packages/branding/marketing/brand.lock.yaml"
    campaign = project / "packages/branding/marketing/campaigns/launch.campaign.yaml"
    metadata_path = project / "marketing.harness.json"
    brand.parent.mkdir(parents=True)
    campaign.parent.mkdir(parents=True)
    brand.write_text(
        """
brand:
  id: test-brand
  name: Test Brand
version: 1.0.0
provider:
  gateway: gpt-image-skill
  params:
    seed_strategy: fixed
    seed: 7
    output_format: png
global:
  style-fragment:
    base:
      $value: clean editorial product lighting
      $type: text
  color:
    primary:
      $value: "#112233"
      $type: color
alias:
  style:
    launch-hero:
      $value:
        prompt: "{global.style-fragment.base}"
        palette:
          - "{global.color.primary}"
        negative: ""
        references: []
      $type: composite
""".lstrip(),
        encoding="utf-8",
    )
    campaign.write_text(
        """
name: launch
brief: Launch image
style: launch-hero
content:
  headline: Hello
  subject: Product on a table
deliverables:
  - id: web-banner
    size: [320, 120]
""".lstrip(),
        encoding="utf-8",
    )
    metadata_path.write_text(json.dumps(metadata(project)), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--metadata",
            str(metadata_path),
            "render",
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    output_dir = project / "packages/branding/.harness/out/launch"
    assert (output_dir / "web-banner.svg").is_file()
    assert (output_dir / "manifest.json").is_file()
