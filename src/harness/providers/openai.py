from __future__ import annotations

import base64
import io
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from PIL import Image, ImageOps

from harness.providers.base import (
    AuthenticationError,
    ContentRejectedError,
    GenerationRequest,
    GenerationResult,
    ImageProvider,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
    TransientProviderError,
)
from harness.providers.gateway import safe_response_text, sanitize_metadata
from harness.providers.placeholder import write_dry_run_asset

OPENAI_IMAGE_ENDPOINT = "/images/generations"
OPENAI_SUPPORTED_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}
OUTPUT_FORMAT_MIME_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}


class OpenAIImageProvider(ImageProvider):
    """OpenAI Images API provider."""

    def generate(self, request: GenerationRequest, output_path: Path) -> GenerationResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if request.dry_run:
            return write_dry_run_asset(request, output_path)

        attempts = max(1, int(request.params.get("retry_attempts", 3)))
        for attempt in range(1, attempts + 1):
            try:
                return self._generate_once(request, output_path)
            except (RateLimitError, ProviderTimeoutError, TransientProviderError):
                if attempt == attempts:
                    raise
                time.sleep(min(2**attempt, 8))

        raise ProviderError("OpenAI provider retry loop exited unexpectedly")

    def _generate_once(self, request: GenerationRequest, output_path: Path) -> GenerationResult:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            raise AuthenticationError("OPENAI_API_KEY is not set")

        endpoint = urljoin(f"{base_url.rstrip('/')}/", OPENAI_IMAGE_ENDPOINT.lstrip("/"))
        timeout = float(request.params.get("timeout_seconds", 120))
        payload = build_openai_payload(request)

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"OpenAI timed out after {timeout:g}s") from exc
        except httpx.HTTPError as exc:
            raise TransientProviderError(f"OpenAI request failed: {exc}") from exc

        raise_for_openai_status(response)
        body = parse_openai_json(response)
        image_bytes = extract_openai_image_bytes(body)
        output_format = normalize_output_format(request.params.get("output_format", "png"))
        write_sized_image(image_bytes, output_path, request.size, output_format)

        openai_size = payload.get("size")
        metadata = {
            "gateway": request.gateway,
            "model": request.model,
            "status_code": response.status_code,
            "openai_size": openai_size,
            "requested_size": list(request.size),
            "resized_to_requested_size": openai_size != f"{request.size[0]}x{request.size[1]}",
            "response": sanitize_metadata(body),
        }
        return GenerationResult(
            asset_id=request.asset_id,
            path=output_path,
            seed=request.seed,
            mime_type=OUTPUT_FORMAT_MIME_TYPES[output_format],
            provider_metadata=metadata,
        )


def build_openai_payload(request: GenerationRequest) -> dict[str, Any]:
    output_format = normalize_output_format(request.params.get("output_format", "png"))
    payload: dict[str, Any] = {
        "model": request.model,
        "prompt": build_openai_prompt(request),
        "size": choose_openai_size(request.size, request.params.get("openai_size")),
        "output_format": output_format,
    }

    for key in ("quality", "background", "moderation"):
        value = request.params.get(key)
        if value is not None:
            payload[key] = value

    if request.model.startswith("dall-e"):
        payload["response_format"] = "b64_json"

    extra = request.params.get("openai_extra")
    if isinstance(extra, dict):
        payload.update(extra)

    return payload


def build_openai_prompt(request: GenerationRequest) -> str:
    parts = [request.prompt]
    if request.negative_prompt:
        parts.append(f"Avoid: {request.negative_prompt}")
    if request.seed is not None:
        parts.append(
            f"Reproducibility hint: preserve deterministic composition family {request.seed}."
        )
    return "\n".join(parts)


def choose_openai_size(target_size: tuple[int, int], override: Any = None) -> str:
    if isinstance(override, str):
        if override not in OPENAI_SUPPORTED_SIZES:
            supported = ", ".join(sorted(OPENAI_SUPPORTED_SIZES))
            raise ProviderError(
                f"unsupported OpenAI image size '{override}'. Supported: {supported}"
            )
        return override

    width, height = target_size
    ratio = width / height
    if ratio > 1.2:
        return "1536x1024"
    if ratio < 0.83:
        return "1024x1536"
    return "1024x1024"


def normalize_output_format(value: Any) -> str:
    output_format = str(value or "png").lower()
    if output_format == "jpg":
        output_format = "jpeg"
    if output_format not in {"png", "jpeg", "webp"}:
        raise ProviderError("OpenAI output_format must be one of: png, jpeg, webp")
    return output_format


def parse_openai_json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise ProviderError("OpenAI response was not valid JSON") from exc
    if not isinstance(body, dict):
        raise ProviderError("OpenAI response JSON must be an object")
    return body


def extract_openai_image_bytes(body: dict[str, Any]) -> bytes:
    data = body.get("data")
    if not isinstance(data, list) or not data:
        raise ProviderError("OpenAI response did not contain image data")

    first = data[0]
    if not isinstance(first, dict):
        raise ProviderError("OpenAI image data entry was not an object")

    image_b64 = first.get("b64_json")
    if isinstance(image_b64, str) and image_b64:
        return base64.b64decode(image_b64)

    image_url = first.get("url")
    if isinstance(image_url, str) and image_url:
        return download_openai_image(image_url)

    raise ProviderError("OpenAI response did not contain b64_json or url")


def download_openai_image(image_url: str) -> bytes:
    try:
        with httpx.Client(timeout=120) as client:
            response = client.get(image_url)
    except httpx.TimeoutException as exc:
        raise ProviderTimeoutError("OpenAI image download timed out") from exc
    except httpx.HTTPError as exc:
        raise TransientProviderError(f"OpenAI image download failed: {exc}") from exc
    raise_for_openai_status(response)
    return response.content


def write_sized_image(
    image_bytes: bytes,
    output_path: Path,
    target_size: tuple[int, int],
    output_format: str,
) -> None:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGBA") if output_format == "png" else image.convert("RGB")
        resized = ImageOps.fit(
            image,
            target_size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        save_format = "JPEG" if output_format == "jpeg" else output_format.upper()
        resized.save(output_path, format=save_format)


def raise_for_openai_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return

    message = safe_response_text(response)
    if response.status_code in (401, 403):
        raise AuthenticationError(f"OpenAI authentication failed ({response.status_code})")
    if response.status_code == 429:
        raise RateLimitError("OpenAI rate limit exceeded")
    if response.status_code in (400, 422) and looks_like_openai_policy_rejection(message):
        raise ContentRejectedError(f"OpenAI rejected content: {message}")
    if response.status_code >= 500:
        raise TransientProviderError(
            f"OpenAI transient failure ({response.status_code}): {message}"
        )
    raise ProviderError(f"OpenAI request failed ({response.status_code}): {message}")


def looks_like_openai_policy_rejection(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ("policy", "safety", "moderation", "rejected"))
