"""The DryRun cascade — the reusable, in-process orchestration of the whole pipeline.

generate -> score viability (whole pool) -> fold-risk (survivors only) -> cost ->
optimize -> report.

This module imports only `dryrun_core` and `dryrun_providers` — NEVER `uagents` —
so it powers the CLI, the FastAPI gateway, and (as a reliable fallback) the
orchestrator agent, all without the agent framework. Provider selection is global
via DRYRUN_MODE, so the exact same code runs the mock demo and the live system.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from dryrun_core.cost_model import estimate_cost
from dryrun_core.embedding import embed, project_2d
from dryrun_core.models import (
    CandidateRow,
    Design,
    FunnelCounts,
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

logger = logging.getLogger("dryrun.cascade")

# A normalized viability score below this is filtered before any expensive folding.
VIABILITY_THRESHOLD = 0.35
# Default cap on how many viability survivors get folded. Mock folding is instant
# so this is generous; the live cascade passes a small cap (DRYRUN_FOLD_CAP) because
# MSA-based AlphaFold2 is slow/expensive.
DEFAULT_FOLD_CAP = 64
_SEQ_PREVIEW = 14


def _normalize(raws: list[float]) -> list[float]:
    if not raws:
        return []
    lo, hi = min(raws), max(raws)
    if hi - lo < 1e-9:
        return [0.5] * len(raws)
    return [(r - lo) / (hi - lo) for r in raws]


def _preview(seq: str) -> str:
    return seq if len(seq) <= _SEQ_PREVIEW else seq[:_SEQ_PREVIEW] + "…"


def _structure_payload(
    design: Design, structure: StructureResult, is_wild_type: bool
) -> StructurePayload:
    return StructurePayload(
        design_id=design.id,
        is_wild_type=is_wild_type,
        pdb=structure.pdb,
        plddt=structure.plddt,
        mean_plddt=round(structure.mean_plddt, 2),
        low_confidence_regions=structure.low_confidence_regions,
        mutation_positions=design.mutation_positions,
        misfold_flag=structure.misfold_flag,
    )


def run_cascade(
    seed_sequence: str,
    goal: str,
    budget: float,
    candidate_count: int,
    *,
    viability_threshold: float = VIABILITY_THRESHOLD,
    fold_cap: int = DEFAULT_FOLD_CAP,
) -> Report:
    """Run the full DryRun cascade in process and return the complete Report."""
    mode = get_mode()
    generation = get_generation_provider()
    viability = get_viability_provider()
    structure = get_structure_provider()
    cost_provider = get_cost_provider()
    llm = get_llm_provider()
    pricing = cost_provider.pricing()

    seed = seed_sequence.strip().upper()
    logger.info("Cascade start: mode=%s n=%d budget=%.0f", mode, candidate_count, budget)

    # 1. Generate candidate variants.
    designs = generation.generate(seed, goal, candidate_count)

    # 2. Score viability on the WHOLE pool (cheap first pass).
    raw_scores = viability.score([d.sequence for d in designs])
    norm_scores = _normalize(raw_scores)
    viability_scores = {
        d.id: ViabilityScore(design_id=d.id, score=ns, raw=rs, method=mode)
        for d, rs, ns in zip(designs, raw_scores, norm_scores)
    }
    viability_survivors = [d for d in designs if viability_scores[d.id].score >= viability_threshold]

    # 3. Fold-risk on survivors only (the expensive step), capped.
    to_fold = viability_survivors[:fold_cap]
    structures: dict[str, StructureResult] = {
        d.id: structure.predict(d.id, d.sequence) for d in to_fold
    }

    # 4. Cost every construct (cheap, whole pool).
    costs = {d.id: estimate_cost(d.id, d.sequence, pricing) for d in designs}

    # 5. Combine into ScoredDesigns (p_i) for the whole pool.
    scored: list[ScoredDesign] = []
    for d in designs:
        struct = structures.get(d.id)
        vs = viability_scores[d.id]
        passed_viability = vs.score >= viability_threshold
        p = success_probability(vs.score, struct)
        scored.append(
            ScoredDesign(
                design=d,
                viability=vs,
                structure=struct,
                cost=costs[d.id],
                embedding=[float(x) for x in embed(d.sequence)],
                success_probability=p,
                passed_viability=passed_viability,
                passed_fold=bool(struct) and not struct.misfold_flag,
            )
        )
    by_id = {sd.id: sd for sd in scored}

    # 6. Optimize over the designs that survived BOTH filters (the buyable pool).
    pool = [sd for sd in scored if sd.passed_fold]
    comparison = build_comparison(pool, budget)
    optimized, naive = comparison.optimized, comparison.naive
    opt_ids = set(optimized.selected_ids)
    naive_ids = set(naive.selected_ids)

    # ---- Assemble the report payload ----
    funnel = FunnelCounts(
        generated=len(designs),
        viability_passed=len(viability_survivors),
        fold_passed=len(pool),
        selected=optimized.count,
    )

    # sequence-space scatter: project EVERY candidate's embedding to 2D.
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

    # structures: wild type + each selected design (for the 3D toggle).
    wt_structure = structure.predict("wild-type", seed)
    wild_type_payload = _structure_payload(
        Design(id="wild-type", sequence=seed, is_wild_type=True), wt_structure, True
    )
    structure_payloads = [
        _structure_payload(by_id[did].design, structures[did], False)
        for did in optimized.selected_ids
        if did in structures
    ]

    # round comparison metrics for honest display
    _round_portfolio(optimized)
    _round_portfolio(naive)
    if comparison.dollars_naive_needs_to_match is not None:
        comparison.dollars_naive_needs_to_match = round(
            comparison.dollars_naive_needs_to_match, 2
        )
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

    plain_summary = llm.summarize(
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
        mode=mode,
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


def _round_portfolio(p) -> None:
    p.total_cost = round(p.total_cost, 2)
    p.expected_successes = round(p.expected_successes, 3)
    p.expected_distinct_successes = round(p.expected_distinct_successes, 3)
    p.cost_per_success = round(p.cost_per_success, 2)
