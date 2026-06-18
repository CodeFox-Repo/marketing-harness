#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
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

INCLUDE_ROOTS = {
    ".github",
    "agents",
    "assets",
    "published",
    "references",
    "scripts",
    "src",
    "tests",
    "workspace",
}

INCLUDE_FILES = {
    ".env.example",
    ".gitattributes",
    ".gitignore",
    "README.md",
    "README.zh-CN.md",
    "SKILL.md",
    "pyproject.toml",
    "uv.lock",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: bootstrap_harness.py <target-dir>", file=sys.stderr)
        return 2

    source_root = Path(__file__).resolve().parents[1]
    target_root = Path(sys.argv[1]).expanduser().resolve()

    if target_root.exists() and any(target_root.iterdir()):
        print(f"target directory is not empty: {target_root}", file=sys.stderr)
        return 1

    target_root.mkdir(parents=True, exist_ok=True)
    for name in sorted(INCLUDE_FILES):
        source = source_root / name
        if source.exists():
            shutil.copy2(source, target_root / name)

    for name in sorted(INCLUDE_ROOTS):
        source = source_root / name
        if source.exists():
            copy_tree(source, target_root / name)

    print(target_root)
    return 0


def copy_tree(source: Path, target: Path) -> None:
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if should_exclude(relative):
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def should_exclude(relative: Path) -> bool:
    return any(part in EXCLUDE_NAMES for part in relative.parts)


if __name__ == "__main__":
    raise SystemExit(main())
