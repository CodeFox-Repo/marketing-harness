from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ProviderError(RuntimeError):
    """Base provider failure."""


class AuthenticationError(ProviderError):
    """Provider rejected or cannot find credentials."""


class RateLimitError(ProviderError):
    """Provider rate limited the request."""


class ContentRejectedError(ProviderError):
    """Provider rejected the content or prompt."""


class ProviderTimeoutError(ProviderError):
    """Provider did not respond inside the configured timeout."""


class TransientProviderError(ProviderError):
    """Provider failure that may succeed on retry."""


@dataclass(frozen=True)
class GenerationRequest:
    asset_id: str
    prompt: str
    negative_prompt: str
    size: tuple[int, int]
    seed: int | None
    gateway: str
    model: str
    params: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    palette: list[str] = field(default_factory=list)
    typography: str | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class GenerationResult:
    asset_id: str
    path: Path
    seed: int | None
    mime_type: str
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class ImageProvider(ABC):
    @abstractmethod
    def generate(self, request: GenerationRequest, output_path: Path) -> GenerationResult:
        """Generate one asset and write it to output_path."""
