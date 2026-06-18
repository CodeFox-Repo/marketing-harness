from __future__ import annotations

import copy
import json
import sys
from typing import Any

import yaml


def token(value: Any, token_type: str) -> dict[str, Any]:
    return {"$value": value, "$type": token_type}


def phrase(*parts: str) -> str:
    return " ".join(parts)


def main() -> int:
    payload = json.load(sys.stdin)
    proposal = copy.deepcopy(payload["base_brand"])
    proposal["version"] = payload["version"]

    provider = proposal.setdefault("provider", {})
    params = provider.setdefault("params", {})
    params["quality"] = "high"
    params["seed"] = 20260619
    params["timeout_seconds"] = max(int(params.get("timeout_seconds", 180)), 240)

    global_tokens = proposal.setdefault("global", {})
    colors = global_tokens.setdefault("color", {})
    colors.update(
        {
            "void": token("#070A0F", "color"),
            "lunar-dust": token("#D8D0C4", "color"),
            "claude-clay": token("#D87857", "color"),
            "signal-cyan": token("#38DDF8", "color"),
            "orbit-blue": token("#2458A7", "color"),
            "instrument-green": token("#8FE6C1", "color"),
        }
    )

    typography = global_tokens.setdefault("typography", {})
    typography["display-face"] = token(
        phrase(
            "large crisp high-contrast serif masthead for Claude,",
            "paired with compact mission-control sans typography",
        ),
        "fontFamily",
    )
    typography["utility-face"] = token(
        phrase(
            "condensed technical sans or monospaced interface labels,",
            "sharp numeric readouts, bilingual text legible at poster distance",
        ),
        "fontFamily",
    )

    fragments = global_tokens.setdefault("style-fragment", {})
    fragments["aerospace-flag"] = token(
        phrase(
            "premium high-technology aerospace campaign poster, one modern fabric flag",
            "as the hero object, cinematic moon-mission composition, precision hardware",
            "realism, controlled heroic scale, strong frontier energy",
        ),
        "text",
    )
    fragments["mission-interface"] = token(
        phrase(
            "transparent mission-control HUD overlays, orbital telemetry arcs, lidar",
            "scan grids, terrain mapping contours, compact rover and sensor cues,",
            "optical blue-cyan signal light, crisp data readouts, disciplined technical",
            "hierarchy",
        ),
        "text",
    )

    negatives = global_tokens.setdefault("negative", {})
    negatives["global-exclude"] = token(
        phrase(
            "garbled text, unreadable typography, malformed Claude word, fake official",
            "seals, fake sponsor logos, watermark, cheap e-commerce flyer, cartoon",
            "astronaut, glossy robot mascot, generic glowing AI sphere, cozy paper",
            "notebook, hand-drawn desk sketch, warm scrapbook editorial, low-tech",
            "workbench props, crowded composition",
        ),
        "text",
    )

    aliases = proposal.setdefault("alias", {}).setdefault("style", {})
    aliases["flag-launch"] = {
        "$type": "composite",
        "$value": {
            "prompt": (
                "{global.style-fragment.aerospace-flag}, "
                "{global.style-fragment.mission-interface}"
            ),
            "palette": [
                "{global.color.void}",
                "{global.color.lunar-dust}",
                "{global.color.claude-clay}",
                "{global.color.signal-cyan}",
                "{global.color.orbit-blue}",
                "{global.color.instrument-green}",
            ],
            "typography": "{global.typography.display-face}; {global.typography.utility-face}",
            "negative": "{global.negative.global-exclude}",
            "references": [],
        },
    }

    yaml.safe_dump(proposal, sys.stdout, sort_keys=False, allow_unicode=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
