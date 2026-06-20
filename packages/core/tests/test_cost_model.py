"""Tests for the synthesis cost model."""

from __future__ import annotations

from dryrun_core.cost_model import (
    PricingParams,
    back_translate,
    estimate_cost,
    gc_content,
    repeat_fraction,
)


def test_back_translate_length_includes_stop() -> None:
    protein = "MKAT"
    dna = back_translate(protein)
    assert len(dna) == len(protein) * 3 + 3  # codons + stop


def test_gc_content_bounds() -> None:
    assert gc_content("") == 0.0
    assert gc_content("GGCC") == 1.0
    assert gc_content("ATAT") == 0.0
    assert 0.0 <= gc_content(back_translate("MKTAYIAKQR")) <= 1.0


def test_repeat_fraction_detects_repeats() -> None:
    assert repeat_fraction("ACGT") == 0.0  # too short for k=10
    repetitive = "AAAAAAAAAAAAAAAAAAAA"  # 20 A's -> heavily repeated 10-mers
    assert repeat_fraction(repetitive) > 0.5


def test_cost_increases_with_length() -> None:
    short = estimate_cost("a", "MKAT")
    long = estimate_cost("b", "MKAT" * 25)
    assert long.total_cost > short.total_cost
    assert long.dna_length_bp > short.dna_length_bp


def test_cost_components_consistent() -> None:
    est = estimate_cost("x", "MKTAYIAKQRQISFVK")
    expected_total = est.base_cost * (1.0 + est.complexity_surcharge) + est.cloning_fee
    assert abs(est.total_cost - expected_total) < 1e-6
    assert est.cloning_fee == 75.0
    assert est.currency == "USD"


def test_pricing_params_flow_through() -> None:
    cheap = PricingParams(per_bp_usd=0.05, cloning_fee_usd=10.0)
    est = estimate_cost("x", "MKTAYIAK", cheap)
    assert est.cloning_fee == 10.0
    # base cost tracks the per-bp rate
    assert abs(est.base_cost - 0.05 * est.dna_length_bp) < 1e-6
