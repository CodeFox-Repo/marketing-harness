#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

VALUE_FLAGS = {
    "--brand",
    "--outputs-dir",
}
DEFAULT_MARKETING_ROOT = "marketing"
DEFAULT_SCRATCH_DIR = ".harness/out"
DEFAULT_APPROVED_DIR = "marketing/approved"


def main() -> int:
    args, metadata_path = extract_option(sys.argv[1:], "--metadata")
    metadata = load_metadata(metadata_path) if metadata_path else {}

    if args[:1] == ["plan"]:
        print_plan(metadata)
        return 0

    if args[:1] == ["check"]:
        return check_project(args[1:], metadata, metadata_path)

    if args[:1] == ["bootstrap"]:
        return bootstrap_project(args[1:], metadata, metadata_path)

    if args[:1] == ["--resolve"]:
        resolution = bundled_cli_command()
        print(" ".join(shell_quote(part) for part in resolution))
        return 0

    command_args = apply_metadata_args(args, metadata)
    command = bundled_cli_command()
    completed = subprocess.run([*command, *command_args], check=False)
    return completed.returncode


def bundled_cli_command() -> list[str]:
    return [sys.executable, str(Path(__file__).resolve().parent / "cli.py")]


def apply_metadata_args(args: list[str], metadata: dict[str, Any]) -> list[str]:
    if not metadata or not args:
        return args

    command = args[0]
    project_root = project_root_for(metadata)
    next_args = list(args)

    if command in {"validate", "render"}:
        campaign = metadata_path(metadata, project_root, "campaign", "path")
        if campaign and not has_positional(next_args, start=1):
            next_args.insert(1, campaign)
        add_option(next_args, "--brand", metadata_path(metadata, project_root, "brand", "lock"))

    if command == "render":
        add_option(
            next_args,
            "--outputs-dir",
            metadata_path(metadata, project_root, "artifacts", "scratch"),
        )

    return next_args


def bootstrap_project(args: list[str], metadata: dict[str, Any], metadata_path: str | None) -> int:
    write = False
    with_example = False
    target = "."
    remaining = list(args)
    while remaining:
        token = remaining.pop(0)
        if token == "--write":
            write = True
        elif token == "--with-example":
            with_example = True
        elif token in {"-h", "--help"}:
            print(
                "usage: harness.py bootstrap [--metadata FILE] "
                "[--write] [--with-example] [target-dir]"
            )
            return 0
        elif token.startswith("-"):
            raise SystemExit(f"unknown bootstrap option: {token}")
        else:
            target = token

    project_root = project_root_for(metadata, fallback=Path(target).resolve())
    plan = project_paths(metadata, project_root)
    dirs = [
        plan["marketing_root"],
        plan["campaigns_dir"],
        plan["references_dir"],
        plan["plans_dir"],
        plan["scratch_dir"],
        plan["approved_dir"],
        plan["accepted_state"].parent,
    ]

    if write:
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
        if with_example:
            copy_example(plan["marketing_root"])

    print_kv(
        {
            "mode": "write" if write else "dry-run",
            "metadata": metadata_path or "",
            "project_root": project_root,
            "marketing_root": plan["marketing_root"],
            "campaigns_dir": plan["campaigns_dir"],
            "references_dir": plan["references_dir"],
            "plans_dir": plan["plans_dir"],
            "scratch_dir": plan["scratch_dir"],
            "approved_dir": plan["approved_dir"],
            "accepted_state": plan["accepted_state"],
            "created": " ".join(str(path) for path in dirs) if write else "",
            "copied_example": str(plan["marketing_root"] / "examples" / "codefox")
            if write and with_example
            else "",
        }
    )
    if not write:
        print(
            "dry_run_note=pass --write to create directories; "
            "no .gitignore or .gitattributes edits are made"
        )
    return 0


def check_project(args: list[str], metadata: dict[str, Any], metadata_path: str | None) -> int:
    target = args[0] if args else "."
    project_root = project_root_for(metadata, fallback=Path(target).resolve())
    paths = project_paths(metadata, project_root)
    image_cli = shutil.which("gpt-image") or ""
    yaml_ready = python_module_available("yaml")

    print_kv(
        {
            "project_root": project_root,
            "metadata": metadata_path or "",
            "marketing_root": paths["marketing_root"],
            "marketing_root_exists": paths["marketing_root"].exists(),
            "brand_lock": metadata_path_value(metadata, "brand", "lock") or "",
            "brand_lock_exists": Path(
                metadata_path_value(metadata, "brand", "lock") or ""
            ).exists()
            if metadata_path_value(metadata, "brand", "lock")
            else False,
            "campaign": metadata_path_value(metadata, "campaign", "path") or "",
            "campaign_exists": Path(
                metadata_path_value(metadata, "campaign", "path") or ""
            ).exists()
            if metadata_path_value(metadata, "campaign", "path")
            else False,
            "scratch_dir": paths["scratch_dir"],
            "approved_dir": paths["approved_dir"],
            "plans_dir": paths["plans_dir"],
            "accepted_state": paths["accepted_state"],
            "accepted_state_exists": paths["accepted_state"].exists(),
            "bundled_cli": Path(__file__).resolve().parent / "cli.py",
            "yaml_ready": yaml_ready,
            "image_cli": image_cli,
            "live_render_ready": bool(image_cli),
            "launcher_ready": yaml_ready,
        }
    )
    return 0 if yaml_ready else 1


def print_plan(metadata: dict[str, Any]) -> None:
    project_root = project_root_for(metadata)
    paths = project_paths(metadata, project_root)
    print_kv(
        {
            "project_root": project_root,
            "marketing_root": paths["marketing_root"],
            "campaigns_dir": paths["campaigns_dir"],
            "references_dir": paths["references_dir"],
            "plans_dir": paths["plans_dir"],
            "scratch_dir": paths["scratch_dir"],
            "approved_dir": paths["approved_dir"],
            "accepted_state": paths["accepted_state"],
            "brand_lock": metadata_path_value(metadata, "brand", "lock") or "",
            "campaign": metadata_path_value(metadata, "campaign", "path") or "",
            "allow_root_workspace_bootstrap": bool_at(
                metadata, False, "policy", "allowRootWorkspaceBootstrap"
            ),
        }
    )


def project_paths(metadata: dict[str, Any], project_root: Path) -> dict[str, Path]:
    marketing_root = path_at(
        metadata, project_root, DEFAULT_MARKETING_ROOT, "project", "marketingRoot"
    )
    scratch_dir = path_at(metadata, project_root, DEFAULT_SCRATCH_DIR, "artifacts", "scratch")
    approved_dir = path_at(metadata, project_root, DEFAULT_APPROVED_DIR, "artifacts", "approved")
    plans_dir = path_at(metadata, project_root, "marketing/plans", "state", "plans")
    accepted_state = path_at(
        metadata,
        project_root,
        "marketing/accepted.yaml",
        "state",
        "accepted",
    )
    campaigns_value = metadata_path_value(metadata, "brand", "campaigns")
    references_value = metadata_path_value(metadata, "brand", "references")
    campaigns_dir = (
        Path(resolve_project_path(project_root, campaigns_value))
        if campaigns_value
        else marketing_root / "campaigns"
    )
    references_dir = (
        Path(resolve_project_path(project_root, references_value))
        if references_value
        else marketing_root / "references"
    )
    return {
        "marketing_root": marketing_root,
        "scratch_dir": scratch_dir,
        "approved_dir": approved_dir,
        "plans_dir": plans_dir,
        "accepted_state": accepted_state,
        "campaigns_dir": campaigns_dir,
        "references_dir": references_dir,
    }


def copy_example(marketing_root: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "codefox"
    target = marketing_root / "examples" / "codefox"
    if not example.is_dir() or target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(example, target)


def load_metadata(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    metadata_path = Path(path).expanduser()
    raw = metadata_path.read_text(encoding="utf-8")
    stripped = raw.lstrip()
    if stripped.startswith("{"):
        data = json.loads(raw)
    else:
        data = parse_simple_yaml(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"{metadata_path}: metadata root must be an object")
    return data


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = strip_comment(line.strip())
        if not stripped:
            continue
        key, sep, value = stripped.partition(":")
        if not sep:
            raise SystemExit(f"unsupported metadata YAML line: {line}")
        key = key.strip()
        value = value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(value)
    return root


def strip_comment(line: str) -> str:
    quote: str | None = None
    for index, char in enumerate(line):
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        if char == "#" and quote is None:
            return line[:index].rstrip()
    return line


def parse_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    return value


def project_root_for(metadata: dict[str, Any], fallback: Path | None = None) -> Path:
    root = string_at(metadata, "project", "root")
    if not root:
        return fallback or Path.cwd()
    root_path = Path(root).expanduser()
    if root_path.is_absolute():
        return root_path.resolve()
    return (fallback or Path.cwd()).joinpath(root_path).resolve()


def path_at(metadata: dict[str, Any], base: Path, default: str, *parts: str) -> Path:
    value = metadata_path_value(metadata, *parts) or default
    return Path(resolve_project_path(base, value))


def metadata_path(metadata: dict[str, Any], project_root: Path, *parts: str) -> str | None:
    value = metadata_path_value(metadata, *parts)
    if not value:
        return None
    return resolve_project_path(project_root, value)


def metadata_path_value(metadata: dict[str, Any], *parts: str) -> str | None:
    value = value_at(metadata, *parts)
    return str(value) if value not in (None, "") else None


def resolve_project_path(project_root: Path, value: object) -> str:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((project_root / path).resolve())


def string_at(metadata: dict[str, Any], *parts: str) -> str | None:
    value = value_at(metadata, *parts)
    if value in (None, ""):
        return None
    return str(value)


def bool_at(metadata: dict[str, Any], default: bool, *parts: str) -> bool:
    value = value_at(metadata, *parts)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return truthy(str(value))


def value_at(metadata: dict[str, Any], *parts: str) -> object | None:
    current: object = metadata
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def extract_option(args: list[str], option: str) -> tuple[list[str], str | None]:
    result: list[str] = []
    value: str | None = None
    iterator = iter(args)
    for token in iterator:
        if token == option:
            try:
                value = next(iterator)
            except StopIteration as exc:
                raise SystemExit(f"{option} requires a value") from exc
        elif token.startswith(f"{option}="):
            value = token.split("=", 1)[1]
        else:
            result.append(token)
    return result, value


def add_option(args: list[str], flag: str, value: str | None) -> None:
    if not value or has_flag(args, flag):
        return
    args.extend([flag, value])


def has_flag(args: list[str], flag: str) -> bool:
    return any(token == flag or token.startswith(f"{flag}=") for token in args)


def has_positional(args: list[str], start: int) -> bool:
    skip_next = False
    for token in args[start:]:
        if skip_next:
            skip_next = False
            continue
        if token in VALUE_FLAGS:
            skip_next = True
            continue
        if any(token.startswith(f"{flag}=") for flag in VALUE_FLAGS):
            continue
        if not token.startswith("-"):
            return True
    return False


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def print_kv(values: dict[str, object]) -> None:
    for key, value in values.items():
        print(f"{key}={value}")


def python_module_available(name: str) -> bool:
    try:
        __import__(name)
    except ImportError:
        return False
    return True


def shell_quote(value: str) -> str:
    if not value or any(char.isspace() or char in "'\"\\$`" for char in value):
        return "'" + value.replace("'", "'\"'\"'") + "'"
    return value


if __name__ == "__main__":
    raise SystemExit(main())
