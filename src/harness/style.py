from __future__ import annotations

import copy
import json
import os
import re
import shlex
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from harness.config import (
    BrandLock,
    ConfigError,
    load_brand,
    validate_alias_references,
    validate_token_tree,
)

HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")
ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@dataclass(frozen=True)
class StyleProposalResult:
    path: Path
    version: str
    producer: str
    reference_count: int


class StyleProducer(ABC):
    @abstractmethod
    def propose(
        self,
        base_brand: dict[str, Any],
        brief: str,
        references: list[Path],
        version: str,
    ) -> dict[str, Any]:
        """Return a full brand.lock mapping."""


class LocalStyleProducer(StyleProducer):
    """Deterministic style proposal producer for scaffolding and tests."""

    def propose(
        self,
        base_brand: dict[str, Any],
        brief: str,
        references: list[Path],
        version: str,
    ) -> dict[str, Any]:
        proposal = copy.deepcopy(base_brand)
        proposal["version"] = version
        ensure_brand_shape(proposal)

        colors = HEX_COLOR_RE.findall(brief)
        if colors:
            set_token(proposal, ("global", "color", "brand-primary"), colors[0], "color")
        if len(colors) > 1:
            set_token(proposal, ("global", "color", "brand-accent"), colors[1], "color")
        if len(colors) > 2:
            set_token(proposal, ("global", "color", "bg-neutral"), colors[2], "color")

        brief_summary = summarize_brief(brief)
        if brief_summary:
            set_token(
                proposal,
                ("global", "style-fragment", "base-aesthetic"),
                (
                    f"{brief_summary}, consistent brand system, production-ready marketing "
                    "visual language, disciplined composition"
                ),
                "text",
            )
            set_token(
                proposal,
                ("global", "style-fragment", "mood-clean"),
                "clean, controlled, legible, spacious, precise, no visual clutter",
                "text",
            )

        asset_references = build_reference_tokens(references)
        if asset_references:
            proposal["global"]["reference"] = asset_references
            main_reference = next(iter(asset_references))
            ensure_style_aliases_reference(proposal, main_reference)

        return proposal


class CommandStyleProducer(StyleProducer):
    """Adapter for an external design skill command.

    The command receives JSON on stdin and must write a complete brand.lock YAML or JSON
    document to stdout.
    """

    def __init__(self, command: str) -> None:
        if not command.strip():
            raise ConfigError("style producer command must be non-empty")
        self.command = command

    def propose(
        self,
        base_brand: dict[str, Any],
        brief: str,
        references: list[Path],
        version: str,
    ) -> dict[str, Any]:
        payload = {
            "version": version,
            "base_brand": base_brand,
            "brief": brief,
            "references": [path.as_posix() for path in references],
            "output_contract": "complete brand.lock YAML or JSON on stdout",
        }
        try:
            completed = subprocess.run(
                shlex.split(self.command),
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise ConfigError(f"style producer command failed to start: {exc}") from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip()[:1000]
            raise ConfigError(
                f"style producer command exited with {completed.returncode}: {stderr}"
            )

        try:
            proposal = yaml.safe_load(completed.stdout) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"style producer command returned invalid YAML/JSON: {exc}") from exc

        if not isinstance(proposal, dict):
            raise ConfigError("style producer command must return a YAML/JSON mapping")
        return proposal


def propose_style(
    *,
    base_path: Path,
    out_path: Path,
    brief_path: Path | None = None,
    source_paths: list[Path] | None = None,
    version: str | None = None,
    producer_name: str = "local",
    producer_command: str | None = None,
) -> StyleProposalResult:
    _brand, base_brand = load_brand(base_path)
    source_paths = source_paths or []
    references = collect_reference_assets(source_paths)
    brief = read_optional_brief(brief_path)
    proposal_version = version or bump_patch_version(str(base_brand["version"]))
    producer = create_style_producer(producer_name, producer_command)
    proposal = producer.propose(base_brand, brief, references, proposal_version)
    proposal["version"] = proposal_version
    validate_brand_mapping(proposal, out_path)
    write_yaml(out_path, proposal)
    return StyleProposalResult(
        path=out_path,
        version=proposal_version,
        producer=producer_name,
        reference_count=len(references),
    )


def promote_style(proposal_path: Path, target_path: Path, version: str | None = None) -> Path:
    _brand, proposal = load_brand(proposal_path)
    if version is not None:
        proposal["version"] = version
    validate_brand_mapping(proposal, target_path)
    write_yaml(target_path, proposal)
    return target_path


def create_style_producer(name: str, command: str | None = None) -> StyleProducer:
    normalized = name.strip().lower()
    if normalized == "local":
        return LocalStyleProducer()
    if normalized == "command":
        resolved_command = command or os.getenv("HARNESS_STYLE_PRODUCER_CMD")
        if not resolved_command:
            raise ConfigError(
                "HARNESS_STYLE_PRODUCER_CMD or --producer-command is required "
                "when --producer command is used"
            )
        return CommandStyleProducer(resolved_command)
    raise ConfigError("unknown style producer; supported producers: local, command")


def collect_reference_assets(paths: list[Path]) -> list[Path]:
    assets: list[Path] = []
    for path in paths:
        if not path.exists():
            raise ConfigError(f"{path}: source path does not exist")
        if path.is_file():
            if path.suffix.lower() in ASSET_EXTENSIONS:
                assets.append(path)
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in ASSET_EXTENSIONS:
                assets.append(child)
    return assets


def read_optional_brief(path: Path | None) -> str:
    if path is None:
        return ""
    if not path.exists():
        raise ConfigError(f"{path}: brief file does not exist")
    return path.read_text(encoding="utf-8").strip()


def ensure_brand_shape(brand: dict[str, Any]) -> None:
    brand.setdefault("global", {})
    brand.setdefault("alias", {})
    brand["global"].setdefault("color", {})
    brand["global"].setdefault("style-fragment", {})
    brand["global"].setdefault("negative", {})
    brand["global"].setdefault("reference", {})
    brand["alias"].setdefault("style", {})


def set_token(brand: dict[str, Any], path: tuple[str, ...], value: Any, token_type: str) -> None:
    node = brand
    for part in path[:-1]:
        node = node.setdefault(part, {})
    node[path[-1]] = {"$value": value, "$type": token_type}


def build_reference_tokens(references: list[Path]) -> dict[str, dict[str, str]]:
    tokens: dict[str, dict[str, str]] = {}
    used_names: set[str] = set()
    for index, path in enumerate(references):
        token_name = "main-visual" if index == 0 else kebab_name(path.stem)
        while token_name in used_names:
            token_name = f"{token_name}-{index + 1}"
        used_names.add(token_name)
        tokens[token_name] = {"$value": path.as_posix(), "$type": "asset"}
    return tokens


def ensure_style_aliases_reference(brand: dict[str, Any], main_reference_name: str) -> None:
    style_aliases = brand.get("alias", {}).get("style", {})
    for token in style_aliases.values():
        if not isinstance(token, dict):
            continue
        value = token.get("$value")
        if not isinstance(value, dict):
            continue
        references = value.get("references")
        if isinstance(references, list) and references:
            continue
        value["references"] = [f"{{global.reference.{main_reference_name}}}"]


def summarize_brief(brief: str) -> str:
    compact = " ".join(line.strip() for line in brief.splitlines() if line.strip())
    compact = HEX_COLOR_RE.sub("", compact)
    compact = " ".join(compact.split())
    return compact[:280].strip(" ,.;")


def bump_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not parts[2].isdigit():
        raise ConfigError(f"cannot bump non-semver version: {version}")
    return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"


def validate_brand_mapping(brand: dict[str, Any], path: Path) -> BrandLock:
    temp_path = Path(str(path))
    try:
        validated = BrandLock.model_validate(brand)
        validate_token_tree(validated.global_tokens, ("global",))
        validate_token_tree(validated.alias_tokens, ("alias",))
        validate_alias_references(validated)
        return validated
    except Exception as exc:
        raise ConfigError(f"{temp_path}: generated brand lock is invalid: {exc}") from exc


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def kebab_name(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = lowered.strip("-")
    return lowered or "reference"
