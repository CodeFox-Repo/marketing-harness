from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from harness.providers.base import ImageProvider, ProviderError
from harness.providers.gateway import GatewayImageProvider
from harness.providers.openai import OpenAIImageProvider
from harness.providers.skill_cli import SkillCliImageProvider

if TYPE_CHECKING:
    from harness.config import ProviderConfig

ProviderFactory = Callable[["ProviderConfig"], ImageProvider]


class UnsupportedProviderError(ProviderError):
    """Raised when brand.lock references a provider gateway with no registered adapter."""


_PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "generic": lambda _config: GatewayImageProvider(),
    "gateway": lambda _config: GatewayImageProvider(),
    "gpt-image-skill": lambda _config: SkillCliImageProvider(),
    "openai": lambda _config: OpenAIImageProvider(),
    "skill-cli": lambda _config: SkillCliImageProvider(),
}


def create_provider(config: ProviderConfig) -> ImageProvider:
    gateway = normalize_gateway(config.gateway)
    factory = _PROVIDER_FACTORIES.get(gateway)
    if factory is None:
        available = ", ".join(available_provider_gateways())
        raise UnsupportedProviderError(
            f"provider.gateway '{config.gateway}' is not registered. "
            f"Available gateways: {available}"
        )
    return factory(config)


def register_provider(gateway: str, factory: ProviderFactory) -> None:
    normalized = normalize_gateway(gateway)
    if not normalized:
        raise ValueError("provider gateway name must be non-empty")
    _PROVIDER_FACTORIES[normalized] = factory


def available_provider_gateways() -> list[str]:
    return sorted(_PROVIDER_FACTORIES)


def normalize_gateway(gateway: str) -> str:
    return gateway.strip().lower()
