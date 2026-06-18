from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from harness.providers.openai import write_sized_image


def test_write_sized_image_resizes_to_requested_deliverable(tmp_path: Path) -> None:
    source = Image.new("RGB", (32, 24), color=(255, 0, 0))
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    output_path = tmp_path / "asset.png"

    write_sized_image(buffer.getvalue(), output_path, (90, 38), "png")

    with Image.open(output_path) as output:
        assert output.size == (90, 38)
        assert output.format == "PNG"
