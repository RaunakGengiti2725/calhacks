"""The in-process DryRun cascade.

generate -> score viability (whole pool) -> fold-risk (survivors only) -> cost ->
optimize -> report. It simply sequences the shared stage functions (see
`stages.py`), so it is byte-for-byte the same logic the specialist uAgents run —
the agent path and this fallback path can never diverge.

Imports only `dryrun_core` + `dryrun_providers` (never `uagents`), so the CLI, the
FastAPI gateway, and the orchestrator's fallback all work without the agent
framework. Provider selection is global via DRYRUN_MODE.
"""

from __future__ import annotations

import logging

from dryrun_agents.shared import stages
from dryrun_core.models import Report
from dryrun_providers import get_mode

logger = logging.getLogger("dryrun.cascade")

VIABILITY_THRESHOLD = stages.VIABILITY_THRESHOLD
DEFAULT_FOLD_CAP = stages.DEFAULT_FOLD_CAP


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
    seed = seed_sequence.strip().upper()
    logger.info("Cascade start: mode=%s n=%d budget=%.0f", get_mode(), candidate_count, budget)

    # 1. Generate candidate variants.
    designs = stages.generate(seed, goal, candidate_count)

    # 2. Score viability on the WHOLE pool (cheap first pass), then filter.
    viability = stages.score_viability(designs)
    survivors = stages.viability_survivors(designs, viability, viability_threshold)

    # 3. Fold-risk on survivors only (the expensive step), capped.
    structures = stages.fold(survivors[:fold_cap])

    # 4. Cost every construct (cheap, whole pool).
    costs = stages.estimate_costs(designs)

    # 5. Combine into ScoredDesigns (p_i).
    scored = stages.build_scored(designs, viability, structures, costs, viability_threshold)

    # 6. Optimize over the designs that survived BOTH filters (the buyable pool).
    pool = [sd for sd in scored if sd.passed_fold]
    comparison = stages.optimize(pool, budget)

    # 7. Assemble the report.
    return stages.assemble_report(
        seed=seed,
        goal=goal,
        budget=budget,
        candidate_count=candidate_count,
        designs=designs,
        scored=scored,
        comparison=comparison,
    )
