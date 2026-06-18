from __future__ import annotations

import hashlib
import html
from pathlib import Path

from harness.providers.base import GenerationRequest, GenerationResult


def write_dry_run_asset(request: GenerationRequest, output_path: Path) -> GenerationResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = request.size
    prompt_hash = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:12]
    title = f"{request.asset_id} - {request.model}"
    subtitle = f"{width}x{height} - seed {request.seed} - {prompt_hash}"
    bar_height = max(12, height // 18)
    panel_x = width * 0.08
    panel_y = height * 0.18
    panel_width = width * 0.84
    panel_height = height * 0.42
    circle_radius = min(width, height) * 0.11
    title_size = max(16, min(width, height) // 18)
    subtitle_size = max(12, min(width, height) // 28)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#F5F5F0"/>
  <rect x="0" y="0" width="{width}" height="{bar_height}" fill="#1A1A2E"/>
  <rect x="{panel_x:.0f}" y="{panel_y:.0f}" width="{panel_width:.0f}"
    height="{panel_height:.0f}" rx="0" fill="#FFFFFF" opacity="0.92"/>
  <circle cx="{width * 0.78:.0f}" cy="{height * 0.35:.0f}" r="{circle_radius:.0f}"
    fill="#E94560" opacity="0.92"/>
  <text x="{panel_x:.0f}" y="{height * 0.72:.0f}" font-family="Arial, sans-serif"
    font-size="{title_size}" fill="#1A1A2E">{html.escape(title)}</text>
  <text x="{panel_x:.0f}" y="{height * 0.80:.0f}" font-family="Arial, sans-serif"
    font-size="{subtitle_size}" fill="#1A1A2E">{html.escape(subtitle)}</text>
</svg>
"""
    output_path.write_text(svg, encoding="utf-8")
    return GenerationResult(
        asset_id=request.asset_id,
        path=output_path,
        seed=request.seed,
        mime_type="image/svg+xml",
        provider_metadata={
            "dry_run": True,
            "gateway": request.gateway,
            "model": request.model,
            "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
        },
    )
