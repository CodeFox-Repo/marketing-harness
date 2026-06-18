from __future__ import annotations

import json
from pathlib import Path

from harness.manifest import checksum_file
from harness.publish import publish_campaign


def write_render_output(root: Path) -> Path:
    output_dir = root / "outputs" / "feature-x-launch"
    output_dir.mkdir(parents=True)
    (output_dir / "web-banner.png").write_bytes(b"image-bytes")
    source_dir = root / "workspace"
    portfolio_dir = source_dir / "portfolios" / "codefox"
    product_dir = source_dir / "products" / "codefox" / "codefox"
    brand_path = product_dir / "brand.lock.yaml"
    brand_meta_path = product_dir / "brand.meta.yaml"
    brand_elements_path = product_dir / "elements.yaml"
    brand_accepted_path = product_dir / "accepted.yaml"
    portfolio_meta_path = portfolio_dir / "portfolio.meta.yaml"
    portfolio_elements_path = portfolio_dir / "elements.yaml"
    portfolio_accepted_path = portfolio_dir / "accepted.yaml"
    campaign_path = product_dir / "campaigns" / "feature-x-launch.campaign.yaml"
    reference_path = product_dir / "references" / "main_visual.png"
    brand_path.parent.mkdir(parents=True)
    portfolio_dir.mkdir(parents=True)
    campaign_path.parent.mkdir(parents=True)
    reference_path.parent.mkdir(parents=True)
    brand_path.write_text(
        "portfolio:\n  id: codefox\n  name: CodeFox\n  version: 1.0.0\n"
        "brand:\n  id: codefox\n  name: CodeFox\nversion: 1.2.3\n"
    )
    portfolio_meta_path.write_text(
        "portfolio:\n  id: codefox\n  name: CodeFox\n  version: 1.0.0\nmetadata_version: 1.0.0\n"
    )
    portfolio_elements_path.write_text(
        "owner:\n  kind: portfolio\n  id: codefox\nrevision: 1\nelements: []\n"
    )
    portfolio_accepted_path.write_text(
        "owner:\n  kind: portfolio\n  id: codefox\nrevision: 1\naccepted: []\n"
    )
    brand_meta_path.write_text(
        "portfolio:\n  id: codefox\n  name: CodeFox\n  version: 1.0.0\n"
        "brand:\n  id: codefox\n  name: CodeFox\nmetadata_version: 1.0.0\n"
    )
    brand_elements_path.write_text(
        "owner:\n  kind: brand\n  portfolio_id: codefox\n  id: codefox\nrevision: 1\nelements: []\n"
    )
    brand_accepted_path.write_text(
        "owner:\n  kind: brand\n  portfolio_id: codefox\n  id: codefox\nrevision: 1\naccepted: []\n"
    )
    campaign_path.write_text("name: feature-x-launch\n")
    reference_path.write_bytes(b"reference-bytes")
    run_lock = {
        "portfolio": {
            "id": "codefox",
            "name": "CodeFox",
            "version": "1.0.0",
        },
        "brand_lock_path": str(brand_path),
        "campaign_path": str(campaign_path),
        "sidecars": {
            "portfolio_meta": {"path": str(portfolio_meta_path)},
            "portfolio_elements": {"path": str(portfolio_elements_path)},
            "portfolio_accepted": {"path": str(portfolio_accepted_path)},
            "brand_meta": {"path": str(brand_meta_path)},
            "brand_elements": {"path": str(brand_elements_path)},
            "brand_accepted": {"path": str(brand_accepted_path)},
        },
        "resolved_style": {
            "references": [str(reference_path)],
        },
    }
    (output_dir / "run.lock.json").write_text(
        json.dumps(run_lock, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "1.0",
        "campaign": "feature-x-launch",
        "portfolio": {
            "id": "codefox",
            "name": "CodeFox",
            "version": "1.0.0",
        },
        "brand": {
            "id": "codefox",
            "name": "CodeFox",
            "version": "1.2.3",
        },
        "brand_lock_version": "1.2.3",
        "generated_at": "2026-06-16T00:00:00+00:00",
        "provider": {
            "gateway": "generic",
            "model": "flux-2-pro",
        },
        "assets": [
            {
                "id": "web-banner",
                "file": "web-banner.png",
                "path": "web-banner.png",
                "url": None,
                "size": [1920, 600],
                "mime_type": "image/png",
                "checksum_sha256": checksum_file(output_dir / "web-banner.png"),
                "seed": 12345,
            }
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return root / "outputs"


def test_repo_publish_dry_run_reports_versioned_repo_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    outputs_dir = write_render_output(tmp_path)
    monkeypatch.setenv("HARNESS_REPO_PUBLISH_DIR", str(tmp_path / "published"))

    result = publish_campaign(
        "feature-x-launch",
        channel="repo",
        outputs_dir=outputs_dir,
        publish=False,
    )

    assert result.dry_run is True
    assert result.release_path == (
        tmp_path / "published" / "products" / "codefox" / "codefox" / "1.2.3"
    )
    assert result.artifacts[0]["url"].startswith("repo://")
    assert not result.release_path.exists()


def test_repo_publish_copies_assets_manifest_and_run_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:
    outputs_dir = write_render_output(tmp_path)
    monkeypatch.setenv("HARNESS_REPO_PUBLISH_DIR", str(tmp_path / "published"))

    result = publish_campaign(
        "feature-x-launch",
        channel="repo",
        outputs_dir=outputs_dir,
        publish=True,
    )

    snapshot_dir = tmp_path / "published" / "products" / "codefox" / "codefox" / "1.2.3"
    portfolio_snapshot_dir = tmp_path / "published" / "portfolios" / "codefox" / "1.0.0"
    artifact_dir = snapshot_dir / "artifacts" / "feature-x-launch"
    published_manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))

    assert result.dry_run is False
    assert result.release_path == snapshot_dir
    assert (artifact_dir / "web-banner.png").read_bytes() == b"image-bytes"
    assert (artifact_dir / "run.lock.json").exists()
    assert (snapshot_dir / "brand" / "brand.lock.yaml").exists()
    assert (snapshot_dir / "campaigns" / "feature-x-launch.campaign.yaml").exists()
    assert (snapshot_dir / "references" / "main_visual.png").read_bytes() == b"reference-bytes"
    assert (snapshot_dir / "portfolio" / "portfolio.meta.yaml").exists()
    assert (snapshot_dir / "metadata" / "brand.meta.yaml").exists()
    assert (snapshot_dir / "metadata" / "elements.yaml").exists()
    assert (portfolio_snapshot_dir / "portfolio.meta.yaml").exists()
    assert (portfolio_snapshot_dir / "elements.yaml").exists()
    assert published_manifest["brand"]["id"] == "codefox"
    assert published_manifest["brand"]["version"] == "1.2.3"
    assert published_manifest["portfolio"]["id"] == "codefox"
    assert published_manifest["portfolio"]["version"] == "1.0.0"
    assert published_manifest["publish_channel"] == "repo"
    assert published_manifest["storage"]["channel"] == "repo"
    assert published_manifest["storage"]["snapshot_path"].endswith(
        "/published/products/codefox/codefox/1.2.3"
    )
    assert published_manifest["storage"]["portfolio_snapshot_path"].endswith(
        "/published/portfolios/codefox/1.0.0"
    )
    assert published_manifest["assets"][0]["path"] == "artifacts/feature-x-launch/web-banner.png"
    assert published_manifest["assets"][0]["url"].endswith("/web-banner.png")
