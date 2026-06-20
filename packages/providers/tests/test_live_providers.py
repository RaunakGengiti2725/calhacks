"""Tests for live providers' graceful fallback + isolated parsers (no network/keys)."""

from __future__ import annotations


def test_live_factory_falls_back_to_mock_without_keys(monkeypatch) -> None:
    monkeypatch.setenv("DRYRUN_MODE", "live")
    for k in ("ASI_ONE_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from dryrun_providers import factory

    # No credentials -> live construction raises -> factory returns the mock impl.
    assert type(factory.get_llm_provider()).__name__ == "MockLLMProvider"
    assert type(factory.get_generation_provider()).__name__ == "MockGenerationProvider"
    assert type(factory.get_viability_provider()).__name__ == "MockViabilityProvider"
    assert type(factory.get_structure_provider()).__name__ == "MockStructureProvider"
    # Cost has no external dependency, so live mode uses the live wrapper directly.
    assert type(factory.get_cost_provider()).__name__ == "LiveCostDataProvider"
    assert factory.get_cost_provider().pricing().per_bp_usd == 0.09


def test_llm_response_parser_is_isolated_and_robust() -> None:
    from dryrun_providers.live.llm import _extract_json

    assert _extract_json('```json\n{"goal": "stability", "budget": 500}\n```') == {
        "goal": "stability",
        "budget": 500,
    }
    assert _extract_json('Here you go: {"a": 1} thanks') == {"a": 1}


def test_structure_low_confidence_region_parser() -> None:
    from dryrun_providers.live.structure import _low_confidence_regions

    plddt = [90.0, 90.0, 40.0, 30.0, 80.0, 45.0]
    assert _low_confidence_regions(plddt) == [(3, 4), (6, 6)]


def test_generation_diff_mutations() -> None:
    from dryrun_providers.live.generation import _diff_mutations

    muts = _diff_mutations("MKAT", "MLAT")
    assert len(muts) == 1 and str(muts[0]) == "K2L"
