"""Tests for the portfolio optimizer — including the credibility-crux contrast."""

from __future__ import annotations

import numpy as np

from dryrun_core.optimizer import (
    build_comparison,
    coverage_value,
    naive_topn_select,
    submodular_greedy_select,
)
from tests.conftest import make_scored


def _clustered_scenario():
    """A cluster of near-identical high-scoring designs + diverse moderate ones.

    Embeddings: cluster members all point along axis 0 (mutually similar, sim=1).
    Diverse members point along distinct orthogonal axes (sim=0 to everything
    else). Naive top-N spends its whole budget inside the redundant cluster;
    DryRun must spread across the diverse approaches.
    """
    designs = []
    # 4 near-identical high-p, high-cost designs (the tempting cluster).
    for i in range(4):
        designs.append(make_scored(f"c{i}", p=0.8, cost=100.0, embedding=[1.0, 0, 0, 0, 0]))
    # 4 diverse moderate-p designs, each its own region of sequence space.
    diverse_p = [0.6, 0.6, 0.55, 0.5]
    for i, p in enumerate(diverse_p):
        axis = [0.0] * 5
        axis[i + 1] = 1.0
        designs.append(make_scored(f"d{i}", p=p, cost=100.0, embedding=axis))
    return designs


def test_submodular_beats_naive_on_distinct_successes() -> None:
    """THE crux: at equal budget, DryRun yields more expected DISTINCT successes."""
    designs = _clustered_scenario()
    budget = 300.0  # room for 3 designs

    comparison = build_comparison(designs, budget)
    opt = comparison.optimized
    naive = comparison.naive

    # Both respect the budget.
    assert opt.total_cost <= budget + 1e-9
    assert naive.total_cost <= budget + 1e-9

    # DryRun strictly wins on the diversity-aware objective...
    assert opt.expected_distinct_successes > naive.expected_distinct_successes
    assert comparison.expected_successes_uplift > 0.0

    # ...even though naive looks better on the naive metric (raw sum of p_i).
    # This is the whole point: naive's "successes" are correlated and redundant.
    assert naive.expected_successes >= opt.expected_successes

    # Naive piles entirely into the redundant cluster; DryRun reaches diverse ones.
    assert all(sid.startswith("c") for sid in naive.selected_ids)
    assert any(sid.startswith("d") for sid in opt.selected_ids)


def test_dollars_naive_needs_to_match_exceeds_budget() -> None:
    designs = _clustered_scenario()
    budget = 300.0
    comparison = build_comparison(designs, budget)
    dollars = comparison.dollars_naive_needs_to_match
    assert dollars is not None
    # Naive ordering needs strictly more money to match DryRun's distinct successes.
    assert dollars > budget


def test_budget_guard_prefers_best_single_when_greedy_starves() -> None:
    """Cost-benefit greedy alone would grab a cheap low-coverage design and then
    be unable to afford the high-coverage one. The budget guard must recover it."""
    cheap = make_scored("cheap", p=0.3, cost=10.0, embedding=[1.0, 0.0])
    rich = make_scored("rich", p=0.95, cost=100.0, embedding=[0.0, 1.0])
    budget = 100.0  # can afford either alone, but not both

    portfolio = submodular_greedy_select([cheap, rich], budget)
    # The guard returns the higher-coverage single element.
    assert portfolio.selected_ids == ["rich"]
    assert portfolio.expected_distinct_successes > 0.9


def test_matches_brute_force_optimum_on_small_pool() -> None:
    """Partial enumeration must find the true optimum when the pool is small."""
    from itertools import combinations

    from dryrun_core.optimizer import _arrays, coverage_value

    designs = _clustered_scenario()
    budget = 300.0
    p, cost, sim = _arrays(designs)

    # Brute force: best coverage over every budget-feasible subset.
    n = len(designs)
    best = 0.0
    for r in range(n + 1):
        for combo in combinations(range(n), r):
            if sum(cost[i] for i in combo) <= budget + 1e-9:
                best = max(best, coverage_value(list(combo), p, sim))

    got = submodular_greedy_select(designs, budget).expected_distinct_successes
    assert abs(got - best) < 1e-9  # greedy + size-3 enumeration is optimal here


def test_coverage_is_monotone_and_submodular() -> None:
    # Two identical points (sim = 1). Marginal gain must diminish.
    p = np.array([0.5, 0.5])
    sim = np.array([[1.0, 1.0], [1.0, 1.0]])
    gain_first = coverage_value([0], p, sim) - coverage_value([], p, sim)
    gain_second = coverage_value([0, 1], p, sim) - coverage_value([0], p, sim)
    assert gain_first > 0.0
    assert gain_second > 0.0
    assert gain_second < gain_first  # diminishing returns (submodularity)


def test_empty_inputs_are_safe() -> None:
    assert submodular_greedy_select([], 100.0).count == 0
    assert naive_topn_select([], 100.0).count == 0
    comparison = build_comparison([], 100.0)
    assert comparison.optimized.count == 0
    assert comparison.dollars_naive_needs_to_match is None


def test_zero_budget_selects_nothing() -> None:
    designs = _clustered_scenario()
    portfolio = submodular_greedy_select(designs, 0.0)
    assert portfolio.count == 0
    assert portfolio.total_cost == 0.0
