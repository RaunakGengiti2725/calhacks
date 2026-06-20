"""Budget-constrained, diversity-aware portfolio optimizer — the heart of DryRun.

THE PROBLEM
-----------
Given candidate designs, each with success probability p_i in [0, 1] and synthesis
cost c_i, and a total budget B, select a subset S maximizing an objective that
combines expected successes with a diversity reward, subject to
sum_{i in S} c_i <= B.

Ranking by p_i and taking the top affordable N (`naive_topn_select`) is the wrong
answer: it piles budget into near-identical high-scoring designs that share hidden
failure modes and fail together. We want *uncorrelated* successes.

THE OBJECTIVE (submodular coverage)
-----------------------------------
Treat each candidate design as a point ("functional approach") in embedding space.
Selecting design i and having it succeed (prob p_i) "covers" approach j to degree
sim(i, j) in [0, 1]. Approach j is achieved if at least one selected design that
succeeds covers it:

    A_j(S) = 1 - prod_{i in S} (1 - p_i * sim(i, j))

The objective is the expected number of *distinct* approaches achieved:

    F(S) = sum_j A_j(S)

F is monotone and submodular (a sum of probabilistic-coverage terms). Adding a
design similar to ones already chosen yields diminishing marginal return, because
the residual (1 - A_j) it can still cover has already been shrunk by its
neighbors. The marginal gain of adding e to S has a clean closed form:

    F(S + e) - F(S) = p_e * sum_j (1 - A_j(S)) * sim(e, j)

so the greedy maintains a per-approach residual r_j = prod_{i in S}(1 - p_i sim_ij)
and updates it multiplicatively — O(n) per step.

THE ALGORITHM (cost-aware greedy) & ITS GUARANTEE
-------------------------------------------------
Budget-constrained submodular maximization is NP-hard. We solve it with the
cost-benefit greedy: repeatedly add the affordable design with the highest
marginal-gain-PER-DOLLAR until no affordable positive-gain design remains.

For a CARDINALITY constraint, greedy on a monotone submodular function has the
famous (1 - 1/e) ~= 0.63 approximation guarantee (Nemhauser-Wolsey-Fisher 1978).
For a BUDGET (knapsack) constraint, cost-benefit greedy ALONE can be arbitrarily
bad in adversarial cases; the standard fix (Khuller-Moss-Naor / Sviridenko) is to
also consider the best single affordable element and return whichever is better —
which restores a constant-factor ((1 - 1/e) with partial enumeration) guarantee.
We implement that guard so the bound we claim is honest.

`naive_topn_select` is provided purely so the UI can show the contrast.
"""

from __future__ import annotations

import numpy as np

from dryrun_core.embedding import similarity_matrix
from dryrun_core.models import Portfolio, PortfolioComparison, ScoredDesign

_EPS = 1e-9


# ---------------------------------------------------------------------------
# Array helpers (the pure numerical core, easy to unit-test in isolation)
# ---------------------------------------------------------------------------


def _arrays(designs: list[ScoredDesign]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p = np.array([d.success_probability for d in designs], dtype=float)
    cost = np.array([d.cost.total_cost for d in designs], dtype=float)
    emb = np.array([d.embedding for d in designs], dtype=float)
    sim = similarity_matrix(emb) if len(designs) else np.zeros((0, 0))
    return p, cost, sim


def coverage_value(selected: list[int], p: np.ndarray, sim: np.ndarray) -> float:
    """F(S): expected number of distinct functional approaches achieved."""
    if not selected:
        return 0.0
    n = sim.shape[0]
    residual = np.ones(n)
    for i in selected:
        residual *= 1.0 - p[i] * sim[i]
    return float(np.sum(1.0 - residual))


def _greedy_indices(
    p: np.ndarray, cost: np.ndarray, sim: np.ndarray, budget: float
) -> list[int]:
    """Cost-benefit greedy: add max marginal-gain-per-dollar affordable design."""
    n = len(p)
    chosen: list[int] = []
    residual = np.ones(n)
    spent = 0.0
    available = list(range(n))
    while True:
        best_idx: int | None = None
        best_ratio = 0.0
        for e in available:
            if cost[e] > budget - spent + _EPS:
                continue
            # marginal gain = p_e * sum_j residual_j * sim_ej
            gain = float(p[e] * np.dot(residual, sim[e]))
            if gain <= _EPS:
                continue
            ratio = gain / cost[e] if cost[e] > _EPS else gain / _EPS
            # ties broken by index order (stable, deterministic)
            if best_idx is None or ratio > best_ratio + 1e-15:
                best_idx = e
                best_ratio = ratio
        if best_idx is None:
            break
        chosen.append(best_idx)
        available.remove(best_idx)
        spent += cost[best_idx]
        residual *= 1.0 - p[best_idx] * sim[best_idx]
    return chosen


def _best_single_affordable(
    p: np.ndarray, cost: np.ndarray, sim: np.ndarray, budget: float
) -> tuple[list[int], float]:
    """The single affordable design with the highest coverage value (budget guard)."""
    best: int | None = None
    best_val = 0.0
    for e in range(len(p)):
        if cost[e] <= budget + _EPS:
            val = coverage_value([e], p, sim)
            if val > best_val:
                best_val = val
                best = e
    return ([best] if best is not None else []), best_val


# ---------------------------------------------------------------------------
# Portfolio assembly
# ---------------------------------------------------------------------------


def _empty_portfolio(method: str, budget: float) -> Portfolio:
    return Portfolio(
        method=method,
        selected_ids=[],
        budget=budget,
        total_cost=0.0,
        expected_successes=0.0,
        expected_distinct_successes=0.0,
        cost_per_success=0.0,
        count=0,
    )


def _portfolio(
    method: str,
    designs: list[ScoredDesign],
    selected: list[int],
    budget: float,
    p: np.ndarray,
    cost: np.ndarray,
    sim: np.ndarray,
) -> Portfolio:
    ids = [designs[i].id for i in selected]
    total = float(sum(cost[i] for i in selected))
    expected = float(sum(p[i] for i in selected))
    distinct = coverage_value(selected, p, sim)
    cost_per_success = total / expected if expected > _EPS else 0.0
    return Portfolio(
        method=method,
        selected_ids=ids,
        budget=budget,
        total_cost=total,
        expected_successes=expected,
        expected_distinct_successes=distinct,
        cost_per_success=cost_per_success,
        count=len(selected),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def submodular_greedy_select(designs: list[ScoredDesign], budget: float) -> Portfolio:
    """The DryRun optimizer: budget-constrained, diversity-aware selection."""
    if not designs:
        return _empty_portfolio("submodular", budget)
    p, cost, sim = _arrays(designs)
    greedy = _greedy_indices(p, cost, sim, budget)
    greedy_val = coverage_value(greedy, p, sim)
    single, single_val = _best_single_affordable(p, cost, sim, budget)
    # Budget-guarded greedy: keep whichever achieves more coverage.
    selected = greedy if greedy_val >= single_val else single
    return _portfolio("submodular", designs, selected, budget, p, cost, sim)


def naive_topn_select(designs: list[ScoredDesign], budget: float) -> Portfolio:
    """Baseline: rank by success probability, take the top affordable designs.

    This is the strategy DryRun beats — it ignores diversity and concentrates
    budget into the highest-scoring (and typically most similar) designs.
    """
    if not designs:
        return _empty_portfolio("naive_topn", budget)
    p, cost, sim = _arrays(designs)
    order = sorted(range(len(designs)), key=lambda i: (-p[i], cost[i], i))
    selected: list[int] = []
    spent = 0.0
    for i in order:
        if spent + cost[i] <= budget + _EPS:
            selected.append(i)
            spent += cost[i]
    return _portfolio("naive_topn", designs, selected, budget, p, cost, sim)


def _dollars_to_match(designs: list[ScoredDesign], target_distinct: float) -> float | None:
    """Extra budget the naive (by-score) ordering needs to match `target_distinct`.

    Walks designs in score order, accumulating cost, and returns the cumulative
    cost at which naive coverage first reaches the target. None if unreachable.
    """
    if not designs:
        return None
    p, cost, sim = _arrays(designs)
    order = sorted(range(len(designs)), key=lambda i: (-p[i], cost[i], i))
    selected: list[int] = []
    spent = 0.0
    for i in order:
        selected.append(i)
        spent += float(cost[i])
        if coverage_value(selected, p, sim) >= target_distinct - _EPS:
            return spent
    return None


def build_comparison(designs: list[ScoredDesign], budget: float) -> PortfolioComparison:
    """Run both strategies at the same budget and assemble the comparison."""
    optimized = submodular_greedy_select(designs, budget)
    naive = naive_topn_select(designs, budget)
    uplift = optimized.expected_distinct_successes - naive.expected_distinct_successes
    dollars = _dollars_to_match(designs, optimized.expected_distinct_successes)
    return PortfolioComparison(
        optimized=optimized,
        naive=naive,
        expected_successes_uplift=uplift,
        dollars_naive_needs_to_match=dollars,
    )


__all__ = [
    "coverage_value",
    "submodular_greedy_select",
    "naive_topn_select",
    "build_comparison",
]
