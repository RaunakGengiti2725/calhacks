"""The cascade as discrete, reusable stage functions.

Each specialist uAgent (Phase 4) wraps exactly one of these, and the in-process
cascade (`run_cascade`) calls them in sequence — so the agent path and the
fallback path can never silently diverge. These functions import only
`dryrun_core` + `dryrun_providers` (never `uagents`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from dryrun_core.cost_model import estimate_cost
from dryrun_core.embedding import embed, project_2d
from dryrun_core.models import (
    CandidateRow,
    CostEstimate,
    Design,
    FunnelCounts,
    PortfolioComparison,
    Report,
    ReportMeta,
    ReportSummary,
    ScoredDesign,
    SequenceSpacePoint,
    StructurePayload,
    StructureResult,
    ViabilityScore,
)
from dryrun_core.optimizer import build_comparison
from dryrun_core.scoring import success_probability
from dryrun_providers import (
    get_cost_provider,
    get_generation_provider,
    get_llm_provider,
    get_mode,
    get_structure_provider,
    get_viability_provider,
)

# A normalized viability score below this is filtered before any expensive folding.
VIABILITY_THRESHOLD = 0.35
# Default cap on how many viability survivors get folded. Mock folding is instant;
# the live cascade passes a small cap (DRYRUN_FOLD_CAP) because AlphaFold2 is slow.
DEFAULT_FOLD_CAP = 64
_SEQ_PREVIEW = 14


def _normalize(raws: list[float]) -> list[float]:
    if not raws:
        return []
    lo, hi = min(raws), max(raws)
    if hi - lo < 1e-9:
        return [0.5] * len(raws)
    return [(r - lo) / (hi - lo) for r in raws]


# ---------------------------------------------------------------------------
# Stages (each is one specialist agent's job)
# ---------------------------------------------------------------------------


def generate(seed_sequence: str, goal: str, n: int) -> list[Design]:
    """Design Generator: propose N candidate variants toward the goal."""
    return get_generation_provider().generate(seed_sequence.strip().upper(), goal, n)


def score_viability(designs: list[Design]) -> dict[str, ViabilityScore]:
    """Sequence Fitness: per-sequence biological-plausibility score (whole pool)."""
    raws = get_viability_provider().score([d.sequence for d in designs])
    norms = _normalize(raws)
    mode = get_mode()
    return {
        d.id: ViabilityScore(design_id=d.id, score=ns, raw=rs, method=mode)
        for d, rs, ns in zip(designs, raws, norms)
    }


def viability_survivors(
    designs: list[Design],
    viability: dict[str, ViabilityScore],
    threshold: float = VIABILITY_THRESHOLD,
) -> list[Design]:
    return [d for d in designs if viability[d.id].score >= threshold]


def fold(designs: list[Design]) -> dict[str, StructureResult]:
    """Fold Risk: structure + confidence (expensive; survivors only)."""
    sp = get_structure_provider()
    return {d.id: sp.predict(d.id, d.sequence) for d in designs}


def estimate_costs(designs: list[Design]) -> dict[str, CostEstimate]:
    """Synthesis Cost: per-construct synthesis + cloning cost."""
    pricing = get_cost_provider().pricing()
    return {d.id: estimate_cost(d.id, d.sequence, pricing) for d in designs}


def build_scored(
    designs: list[Design],
    viability: dict[str, ViabilityScore],
    structures: dict[str, StructureResult],
    costs: dict[str, CostEstimate],
    threshold: float = VIABILITY_THRESHOLD,
) -> list[ScoredDesign]:
    """Combine viability + structure + cost + embedding into ScoredDesigns (p_i)."""
    scored: list[ScoredDesign] = []
    for d in designs:
        struct = structures.get(d.id)
        vs = viability[d.id]
        scored.append(
            ScoredDesign(
                design=d,
                viability=vs,
                structure=struct,
                cost=costs[d.id],
                embedding=[float(x) for x in embed(d.sequence)],
                success_probability=success_probability(vs.score, struct),
                passed_viability=vs.score >= threshold,
                passed_fold=bool(struct) and not struct.misfold_flag,
            )
        )
    return scored


def optimize(pool: list[ScoredDesign], budget: float) -> PortfolioComparison:
    """Portfolio Optimizer: budget-constrained, diversity-aware selection + naive."""
    return build_comparison(pool, budget)


# ---------------------------------------------------------------------------
# Reporting stage
# ---------------------------------------------------------------------------


def _preview(seq: str) -> str:
    return seq if len(seq) <= _SEQ_PREVIEW else seq[:_SEQ_PREVIEW] + "…"


def _structure_payload(design: Design, structure: StructureResult, is_wt: bool) -> StructurePayload:
    return StructurePayload(
        design_id=design.id,
        is_wild_type=is_wt,
        pdb=structure.pdb,
        plddt=structure.plddt,
        mean_plddt=round(structure.mean_plddt, 2),
        low_confidence_regions=structure.low_confidence_regions,
        mutation_positions=design.mutation_positions,
        misfold_flag=structure.misfold_flag,
    )


def _round_portfolio(p) -> None:
    p.total_cost = round(p.total_cost, 2)
    p.expected_successes = round(p.expected_successes, 3)
    p.expected_distinct_successes = round(p.expected_distinct_successes, 3)
    p.cost_per_success = round(p.cost_per_success, 2)


def assemble_report(
    *,
    seed: str,
    goal: str,
    budget: float,
    candidate_count: int,
    designs: list[Design],
    scored: list[ScoredDesign],
    comparison: PortfolioComparison,
) -> Report:
    """Reporting: assemble the single typed payload the frontend renders."""
    by_id = {sd.id: sd for sd in scored}
    structures = {sd.id: sd.structure for sd in scored if sd.structure is not None}
    optimized, naive = comparison.optimized, comparison.naive
    opt_ids = set(optimized.selected_ids)
    naive_ids = set(naive.selected_ids)

    funnel = FunnelCounts(
        generated=len(designs),
        viability_passed=sum(1 for sd in scored if sd.passed_viability),
        fold_passed=sum(1 for sd in scored if sd.passed_fold),
        selected=optimized.count,
    )

    coords = project_2d([sd.embedding for sd in scored]) if scored else []
    sequence_space = [
        SequenceSpacePoint(
            design_id=sd.id,
            x=round(x, 4),
            y=round(y, 4),
            selected_optimized=sd.id in opt_ids,
            selected_naive=sd.id in naive_ids,
            success_probability=round(sd.success_probability, 4),
        )
        for sd, (x, y) in zip(scored, coords)
    ]

    candidates = [
        CandidateRow(
            design_id=sd.id,
            sequence_preview=_preview(sd.design.sequence),
            viability=round(sd.viability.score, 3),
            fold_confidence=round(sd.structure.mean_plddt, 1) if sd.structure else None,
            cost=round(sd.cost.total_cost, 2),
            success_probability=round(sd.success_probability, 3),
            selected=sd.id in opt_ids,
            selected_naive=sd.id in naive_ids,
            mutations=[str(m) for m in sd.design.mutations],
        )
        for sd in scored
    ]

    wt_structure = get_structure_provider().predict("wild-type", seed)
    wild_type_payload = _structure_payload(
        Design(id="wild-type", sequence=seed, is_wild_type=True), wt_structure, True
    )
    structure_payloads = [
        _structure_payload(by_id[did].design, structures[did], False)
        for did in optimized.selected_ids
        if did in structures
    ]

    _round_portfolio(optimized)
    _round_portfolio(naive)
    if comparison.dollars_naive_needs_to_match is not None:
        comparison.dollars_naive_needs_to_match = round(comparison.dollars_naive_needs_to_match, 2)
    comparison.expected_successes_uplift = round(comparison.expected_successes_uplift, 3)

    uplift_ratio = (
        optimized.expected_distinct_successes / naive.expected_distinct_successes
        if naive.expected_distinct_successes > 1e-9
        else 1.0
    )
    summary = ReportSummary(
        designs_selected=optimized.count,
        designs_total=len(designs),
        spend=round(optimized.total_cost, 2),
        budget=round(budget, 2),
        expected_distinct_successes=optimized.expected_distinct_successes,
        naive_expected_distinct_successes=naive.expected_distinct_successes,
        expected_constructs=optimized.expected_successes,
        naive_expected_constructs=naive.expected_successes,
        cost_per_success=optimized.cost_per_success,
        uplift_ratio=round(uplift_ratio, 2),
    )

    plain_summary = get_llm_provider().summarize(
        {
            "designs_selected": optimized.count,
            "designs_total": len(designs),
            "spend": optimized.total_cost,
            "budget": budget,
            "expected_distinct_successes": optimized.expected_distinct_successes,
            "naive_expected_distinct_successes": naive.expected_distinct_successes,
            "cost_per_success": optimized.cost_per_success,
            "dollars_naive_needs_to_match": comparison.dollars_naive_needs_to_match,
            "goal": goal,
        }
    )

    meta = ReportMeta(
        mode=get_mode(),
        goal=goal,
        seed_sequence=seed,
        seed_length=len(seed),
        candidate_count=candidate_count,
        budget=budget,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    return Report(
        summary=summary,
        funnel=funnel,
        comparison=comparison,
        candidates=candidates,
        sequence_space=sequence_space,
        structures=structure_payloads,
        wild_type_structure=wild_type_payload,
        plain_summary=plain_summary,
        meta=meta,
    )
