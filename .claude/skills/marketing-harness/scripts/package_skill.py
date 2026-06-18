#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def main() -> int:
    skill_dir = Path(__file__).resolve().parents[1]
    default_output = skill_dir.parent / f"{skill_dir.name}.zip"
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_output
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(skill_dir))

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
