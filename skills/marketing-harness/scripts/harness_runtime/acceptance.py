from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness_runtime.manifest import checksum_file


@dataclass(frozen=True)
class AcceptedAssetDraft:
    entry: dict[str, Any]
    source_path: Path
    approved_path: Path
    manifest_path: Path
    run_lock_path: Path | None


def build_accepted_asset_draft(
    *,
    output_dir: Path,
    approved_root: Path,
    asset_id: str,
    notes: str,
    tags: list[str] | None = None,
) -> AcceptedAssetDraft:
    """Build the state entry an agent should write after user acceptance."""
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"{manifest_path} does not exist; render candidates first")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset = find_manifest_asset(manifest, asset_id)
    campaign = str(manifest["campaign"])
    brand = brand_info(manifest)
    portfolio = portfolio_info(manifest, brand)
    source_path = output_dir / str(asset["file"])
    approved_dir = (
        approved_root
        / "products"
        / portfolio["id"]
        / brand["id"]
        / brand["version"]
        / "artifacts"
        / campaign
    )
    approved_path = approved_dir / str(asset["file"])
    run_lock_path = output_dir / "run.lock.json"
    return AcceptedAssetDraft(
        entry={
            "id": f"{campaign}-{asset_id}",
            "kind": "artifact",
            "campaign": campaign,
            "asset_id": asset_id,
            "path": approved_path.as_posix(),
            "manifest": (approved_dir / "manifest.json").as_posix(),
            "run_lock": run_lock_path.as_posix() if run_lock_path.exists() else None,
            "checksum_sha256": checksum_file(source_path),
            "tags": tags or [],
            "notes": notes,
        },
        source_path=source_path,
        approved_path=approved_path,
        manifest_path=manifest_path,
        run_lock_path=run_lock_path if run_lock_path.exists() else None,
    )


def find_manifest_asset(manifest: dict[str, Any], asset_id: str) -> dict[str, Any]:
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("manifest.assets must be a list")
    for asset in assets:
        if isinstance(asset, dict) and asset.get("id") == asset_id:
            return asset
    raise ValueError(f"asset id not found in manifest: {asset_id}")


def brand_info(manifest: dict[str, Any]) -> dict[str, str]:
    brand = manifest.get("brand")
    if isinstance(brand, dict):
        brand_id = str(brand.get("id") or "unknown-brand")
        brand_name = str(brand.get("name") or brand_id)
        brand_version = str(brand.get("version") or manifest.get("brand_lock_version") or "0.0.0")
    else:
        brand_id = "unknown-brand"
        brand_name = "Unknown Brand"
        brand_version = str(manifest.get("brand_lock_version") or "0.0.0")
    return {
        "id": safe_path_segment(brand_id, "brand id"),
        "name": brand_name,
        "version": safe_version_segment(brand_version),
    }


def portfolio_info(manifest: dict[str, Any], brand: dict[str, str]) -> dict[str, str]:
    portfolio = manifest.get("portfolio")
    if isinstance(portfolio, dict):
        portfolio_id = str(portfolio.get("id") or brand["id"])
        portfolio_name = str(portfolio.get("name") or portfolio_id)
        portfolio_version = str(portfolio.get("version") or brand["version"])
    else:
        portfolio_id = brand["id"]
        portfolio_name = brand["name"]
        portfolio_version = brand["version"]
    return {
        "id": safe_path_segment(portfolio_id, "portfolio id"),
        "name": portfolio_name,
        "version": safe_version_segment(portfolio_version),
    }


def safe_path_segment(value: str, label: str) -> str:
    if not value or "/" in value or value in {".", ".."}:
        raise ValueError(f"{label} is not safe for accepted asset paths: {value}")
    return value


def safe_version_segment(value: str) -> str:
    if "/" in value or value in {"", ".", ".."}:
        raise ValueError(f"brand version is not safe for accepted asset paths: {value}")
    return value
