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
    params["seed"] = 20260620
    params["timeout_seconds"] = max(int(params.get("timeout_seconds", 180)), 240)

    global_tokens = proposal.setdefault("global", {})
    colors = global_tokens.setdefault("color", {})
    colors.update(
        {
            "space-black": token("#05070B", "color"),
            "ceramic-white": token("#E7E2D8", "color"),
            "lunar-silver": token("#A9B0B6", "color"),
            "claude-clay": token("#D87857", "color"),
            "engine-blue": token("#56B8FF", "color"),
            "graphite-metal": token("#2A2D31", "color"),
        }
    )

    typography = global_tokens.setdefault("typography", {})
    typography["display-face"] = token(
        "large crisp high-contrast Claude masthead with aerospace campaign restraint",
        "fontFamily",
    )
    typography["utility-face"] = token(
        phrase(
            "compact aerospace stencil sans or precise technical grotesk",
            "for short labels, bilingual text clear and sparse",
        ),
        "fontFamily",
    )

    fragments = global_tokens.setdefault("style-fragment", {})
    fragments["hardware-frontier"] = token(
        phrase(
            "premium cinematic aerospace hardware campaign poster, physical technology",
            "drives the image, believable moon mission equipment, frontier-scale",
            "engineering, no decorative interface layer",
        ),
        "text",
    )
    fragments["lunar-machinery"] = token(
        phrase(
            "dominant real objects: tall lunar landing rocket or ascent vehicle, compact",
            "lander with folded legs, thruster bells, rover, solar-panel wings, antenna",
            "mast, mechanical arm, instrument packages, cable umbilicals, truss",
            "structures, dust-covered brushed titanium, ceramic white shells, graphite",
            "thermal blankets, blue-white engine or sensor light",
        ),
        "text",
    )

    negatives = global_tokens.setdefault("negative", {})
    negatives["global-exclude"] = token(
        phrase(
            "garbled text, unreadable typography, malformed Claude word, fake official",
            "seals, fake sponsor logos, watermark, cheap e-commerce flyer, cartoon",
            "astronaut, glossy robot mascot, generic glowing AI sphere, plastic UI",
            "panels, HUD overlays, floating dashboard widgets, holographic interface",
            "screens, cyberpunk neon city, cozy paper notebook, hand-drawn desk sketch,",
            "warm scrapbook editorial, crowded composition",
        ),
        "text",
    )

    aliases = proposal.setdefault("alias", {}).setdefault("style", {})
    aliases["flag-launch"] = {
        "$type": "composite",
        "$value": {
            "prompt": (
                "{global.style-fragment.hardware-frontier}, "
                "{global.style-fragment.lunar-machinery}"
            ),
            "palette": [
                "{global.color.space-black}",
                "{global.color.ceramic-white}",
                "{global.color.lunar-silver}",
                "{global.color.claude-clay}",
                "{global.color.engine-blue}",
                "{global.color.graphite-metal}",
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
