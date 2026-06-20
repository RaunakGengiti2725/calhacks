"""Provider factory — reads DRYRUN_MODE once and returns the right implementation.

This is the single switch the whole prime directive hinges on. Every getter:
  * returns the Mock implementation when DRYRUN_MODE != "live" (the default), and
  * returns the Live implementation when DRYRUN_MODE == "live", but if Live
    construction fails (missing key, import error), logs a clear warning and
    falls back to Mock so the demo never hard-crashes.

Live implementations are imported lazily inside each getter so the mock path
never needs the live dependencies present.
"""

from __future__ import annotations

import logging
import os
from typing import Callable, TypeVar

from dryrun_providers.base import (
    CostDataProvider,
    GenerationProvider,
    LLMProvider,
    StructureProvider,
    ViabilityProvider,
)

logger = logging.getLogger("dryrun.providers")

T = TypeVar("T")


def get_mode() -> str:
    """The global mode: "mock" (default) or "live"."""
    return os.getenv("DRYRUN_MODE", "mock").strip().lower()


def is_live() -> bool:
    return get_mode() == "live"


def _select(name: str, live_factory: Callable[[], T], mock_factory: Callable[[], T]) -> T:
    """Return live impl in live mode (falling back to mock on any failure), else mock."""
    if not is_live():
        return mock_factory()
    try:
        impl = live_factory()
        logger.info("Using LIVE provider for %s", name)
        return impl
    except Exception as exc:  # noqa: BLE001 — graceful degradation is the whole point
        logger.warning(
            "Live provider for %s unavailable (%s). Falling back to mock.", name, exc
        )
        return mock_factory()


def get_llm_provider() -> LLMProvider:
    def live() -> LLMProvider:
        from dryrun_providers.live.llm import LiveLLMProvider

        return LiveLLMProvider()

    def mock() -> LLMProvider:
        from dryrun_providers.mock.llm import MockLLMProvider

        return MockLLMProvider()

    return _select("LLMProvider", live, mock)


def get_generation_provider() -> GenerationProvider:
    def live() -> GenerationProvider:
        from dryrun_providers.live.generation import LiveGenerationProvider

        return LiveGenerationProvider()

    def mock() -> GenerationProvider:
        from dryrun_providers.mock.generation import MockGenerationProvider

        return MockGenerationProvider()

    return _select("GenerationProvider", live, mock)


def get_viability_provider() -> ViabilityProvider:
    def live() -> ViabilityProvider:
        from dryrun_providers.live.viability import LiveViabilityProvider

        return LiveViabilityProvider()

    def mock() -> ViabilityProvider:
        from dryrun_providers.mock.viability import MockViabilityProvider

        return MockViabilityProvider()

    return _select("ViabilityProvider", live, mock)


def get_structure_provider() -> StructureProvider:
    def live() -> StructureProvider:
        from dryrun_providers.live.structure import LiveStructureProvider

        return LiveStructureProvider()

    def mock() -> StructureProvider:
        from dryrun_providers.mock.structure import MockStructureProvider

        return MockStructureProvider()

    return _select("StructureProvider", live, mock)


def get_cost_provider() -> CostDataProvider:
    def live() -> CostDataProvider:
        from dryrun_providers.live.cost import LiveCostDataProvider

        return LiveCostDataProvider()

    def mock() -> CostDataProvider:
        from dryrun_providers.mock.cost import MockCostDataProvider

        return MockCostDataProvider()

    return _select("CostDataProvider", live, mock)


__all__ = [
    "get_mode",
    "is_live",
    "get_llm_provider",
    "get_generation_provider",
    "get_viability_provider",
    "get_structure_provider",
    "get_cost_provider",
]
