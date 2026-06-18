from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

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
from harness.providers.placeholder import write_dry_run_asset

SENSITIVE_KEY_PARTS = ("key", "token", "secret", "authorization", "credential", "password")
IMAGE_PAYLOAD_KEYS = {"b64_json", "base64", "image"}


class GatewayImageProvider(ImageProvider):
    """HTTP implementation for a unified image-generation gateway."""

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

        raise ProviderError("provider retry loop exited unexpectedly")

    def _generate_once(self, request: GenerationRequest, output_path: Path) -> GenerationResult:
        api_key = os.getenv("HARNESS_GATEWAY_API_KEY")
        base_url = os.getenv("HARNESS_GATEWAY_BASE_URL")
        image_path = os.getenv("HARNESS_GATEWAY_IMAGE_PATH") or "/v1/images/generations"

        if not api_key:
            raise AuthenticationError("HARNESS_GATEWAY_API_KEY is not set")
        if not base_url:
            raise ProviderError("HARNESS_GATEWAY_BASE_URL is not set")

        endpoint = urljoin(f"{base_url.rstrip('/')}/", image_path.lstrip("/"))
        width, height = request.size
        payload = {
            "gateway": request.gateway,
            "model": request.model,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": width,
            "height": height,
            "seed": request.seed,
            "params": provider_payload_params(request.params),
            "references": request.references,
            "palette": request.palette,
            "typography": request.typography,
        }
        timeout = float(request.params.get("timeout_seconds", 120))

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
            raise ProviderTimeoutError(f"gateway timed out after {timeout:g}s") from exc
        except httpx.HTTPError as exc:
            raise TransientProviderError(f"gateway request failed: {exc}") from exc

        self._raise_for_status(response)

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError("gateway response was not valid JSON") from exc

        image_url = extract_image_url(body)
        image_b64 = extract_image_b64(body)
        content_type = "image/png"

        if image_url:
            content_type = self._download_image(image_url, output_path, timeout)
        elif image_b64:
            output_path.write_bytes(decode_b64_image(image_b64))
        else:
            raise ProviderError("gateway response did not contain an image URL or base64 image")

        metadata = {
            "gateway": request.gateway,
            "model": request.model,
            "status_code": response.status_code,
            "source_url": redact_url(image_url) if image_url else None,
            "response": sanitize_metadata(body),
        }
        return GenerationResult(
            asset_id=request.asset_id,
            path=output_path,
            seed=request.seed,
            mime_type=content_type,
            provider_metadata=metadata,
        )

    def _download_image(self, image_url: str, output_path: Path, timeout: float) -> str:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(image_url)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"image download timed out after {timeout:g}s") from exc
        except httpx.HTTPError as exc:
            raise TransientProviderError(f"image download failed: {exc}") from exc

        self._raise_for_status(response)
        output_path.write_bytes(response.content)
        return response.headers.get("content-type", "image/png").split(";")[0]

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return

        message = safe_response_text(response)
        if response.status_code in (401, 403):
            raise AuthenticationError(f"gateway authentication failed ({response.status_code})")
        if response.status_code == 429:
            raise RateLimitError("gateway rate limit exceeded")
        if response.status_code in (400, 422) and looks_like_policy_rejection(message):
            raise ContentRejectedError(f"gateway rejected content: {message}")
        if response.status_code >= 500:
            raise TransientProviderError(
                f"gateway transient failure ({response.status_code}): {message}"
            )
        raise ProviderError(f"gateway request failed ({response.status_code}): {message}")

def extract_image_url(body: Any) -> str | None:
    candidates: list[Any] = []
    if isinstance(body, dict):
        candidates.extend([body.get("url"), body.get("image_url")])
        candidates.append(body.get("output"))
        candidates.append(body.get("images"))
        candidates.append(body.get("data"))

    for candidate in flatten_candidates(candidates):
        if isinstance(candidate, dict):
            for key in ("url", "image_url", "asset_url"):
                value = candidate.get(key)
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    return value
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            return candidate
    return None


def extract_image_b64(body: Any) -> str | None:
    candidates: list[Any] = []
    if isinstance(body, dict):
        candidates.extend([body.get("b64_json"), body.get("image"), body.get("base64")])
        candidates.append(body.get("data"))
        candidates.append(body.get("images"))

    for candidate in flatten_candidates(candidates):
        if isinstance(candidate, dict):
            for key in ("b64_json", "image", "base64"):
                value = candidate.get(key)
                if isinstance(value, str):
                    return value
        if isinstance(candidate, str) and not candidate.startswith(("http://", "https://")):
            return candidate
    return None


def flatten_candidates(values: list[Any]):
    for value in values:
        if isinstance(value, list):
            yield from flatten_candidates(value)
        else:
            yield value


def decode_b64_image(value: str) -> bytes:
    if "," in value and value.strip().startswith("data:"):
        value = value.split(",", 1)[1]
    return base64.b64decode(value)


def safe_response_text(response: httpx.Response) -> str:
    text = response.text[:500].replace("\n", " ").strip()
    return text or response.reason_phrase


def looks_like_policy_rejection(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ("policy", "safety", "moderation", "rejected"))


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lowered_key = key.lower()
            if lowered_key in IMAGE_PAYLOAD_KEYS:
                sanitized[key] = "[redacted image payload]"
            elif any(part in lowered_key for part in SENSITIVE_KEY_PARTS):
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = sanitize_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return redact_url(value)
    if isinstance(value, str) and len(value) > 2000:
        return "[redacted large string]"
    return value


def redact_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.query:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "[redacted]", parsed.fragment))


def provider_payload_params(params: dict[str, Any]) -> dict[str, Any]:
    control_keys = {"seed_strategy", "seed", "timeout_seconds", "retry_attempts", "output_format"}
    return {key: value for key, value in params.items() if key not in control_keys}
