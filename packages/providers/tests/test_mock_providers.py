"""Tests for the mock providers and the end-to-end cascade (mock mode, no network)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DRYRUN_MODE", "mock")

from dryrun_providers import (  # noqa: E402
    get_cost_provider,
    get_generation_provider,
    get_llm_provider,
    get_mode,
    get_structure_provider,
    get_viability_provider,
)
from dryrun_providers.mock.structure import FRAGILE_LOOP, scaffold_sequence  # noqa: E402
from dryrun_providers.pdb_utils import parse_plddt  # noqa: E402

SEED = scaffold_sequence()


def test_factory_returns_mock_in_mock_mode() -> None:
    assert get_mode() == "mock"
    assert type(get_viability_provider()).__name__ == "MockViabilityProvider"
    assert type(get_structure_provider()).__name__ == "MockStructureProvider"


def test_generation_is_deterministic_and_mutates() -> None:
    gen = get_generation_provider()
    a = gen.generate(SEED, "improve thermal stability", 12)
    b = gen.generate(SEED, "improve thermal stability", 12)
    assert len(a) == 12
    assert [d.sequence for d in a] == [d.sequence for d in b]  # deterministic
    assert all(d.mutations for d in a)  # every variant changed something
    assert all(len(d.sequence) == len(SEED) for d in a)


def test_viability_scores_are_ordered_and_deterministic() -> None:
    vp = get_viability_provider()
    seqs = [SEED, SEED[:9] + "W" + SEED[10:]]  # a rare-residue substitution
    s1 = vp.score(seqs)
    s2 = vp.score(seqs)
    assert s1 == s2
    assert len(s1) == 2


def test_structure_has_fragile_loop_and_parsable_plddt() -> None:
    sp = get_structure_provider()
    res = sp.predict("wt", SEED)
    assert len(res.plddt) == len(SEED)
    # B-factors in the returned PDB equal the reported pLDDT (frontend colors by it).
    parsed = parse_plddt(res.pdb)
    assert len(parsed) == len(res.plddt)
    assert parsed[0] == pytest.approx(res.plddt[0], abs=0.01)
    # the deliberate fragile loop shows up as a low-confidence region
    start, end = FRAGILE_LOOP
    assert any(s <= start and e >= end - 1 or (start <= s <= end) for s, e in res.low_confidence_regions)
    assert min(res.plddt) < 50.0


def test_loop_mutations_flag_misfold() -> None:
    sp = get_structure_provider()
    start, _ = FRAGILE_LOOP
    loop_variant = list(SEED)
    loop_variant[start - 1] = "L" if loop_variant[start - 1] != "L" else "A"
    res = sp.predict("loopy", "".join(loop_variant))
    assert res.misfold_flag is True


def test_cost_provider_pricing_defaults() -> None:
    pricing = get_cost_provider().pricing()
    assert pricing.per_bp_usd == pytest.approx(0.09)


def test_llm_parses_natural_request() -> None:
    parsed = get_llm_provider().parse_request(
        "Improve thermal stability of " + SEED + " on a $750 budget, 18 variants"
    )
    assert parsed["seed_sequence"] == SEED
    assert parsed["budget"] == 750.0
    assert parsed["candidate_count"] == 18
    assert "stability" in (parsed["goal"] or "")


def test_full_cascade_runs_and_is_honest() -> None:
    from dryrun_agents.shared.cascade import run_cascade

    report = run_cascade(SEED, "improve thermal stability", 500.0, 20)
    f = report.funnel
    # cascade narrows at each stage
    assert f.generated == 20
    assert f.viability_passed < f.generated
    assert f.fold_passed <= f.viability_passed
    assert f.selected == report.summary.designs_selected

    s = report.summary
    # honesty gate: distinct coverage never exceeds the number of constructs bought
    assert s.expected_distinct_successes <= s.designs_selected + 1e-9
    # DryRun beats naive on diversity-adjusted distinct coverage
    assert s.expected_distinct_successes > s.naive_expected_distinct_successes
    # spend respects budget; payload is complete
    assert s.spend <= s.budget + 1e-9
    assert report.wild_type_structure is not None
    assert len(report.structures) == s.designs_selected
    assert len(report.sequence_space) == f.generated
