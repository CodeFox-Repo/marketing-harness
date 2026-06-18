#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

EXCLUDE_NAMES = {
    ".DS_Store",
    ".env",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-venv",
    ".venv",
    "__pycache__",
    "outputs",
    "releases",
}


def main() -> int:
    skill_dir = Path(__file__).resolve().parents[1]
    default_output = skill_dir.parent / f"{skill_dir.name}.zip"
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_output
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill_dir.rglob("*")):
            relative = path.relative_to(skill_dir)
            if should_exclude(relative) or path.resolve() == output:
                continue
            if path.is_file():
                archive.write(path, arcname=relative)

    print(output)
    return 0


def should_exclude(relative: Path) -> bool:
    return any(part in EXCLUDE_NAMES for part in relative.parts)


if __name__ == "__main__":
    raise SystemExit(main())
