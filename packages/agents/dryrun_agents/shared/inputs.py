"""Resolve a request (natural language + explicit fields) into cascade inputs.

Shared by the CLI and the FastAPI gateway so both interpret requests identically.
Uses the LLM provider (mock or live) to parse free text, then fills any gaps with
the bundled demo defaults.
"""

from __future__ import annotations

from typing import Optional

from dryrun_agents.shared.demo import (
    DEMO_BUDGET,
    DEMO_CANDIDATES,
    DEMO_GOAL,
    DEMO_SEED,
)
from dryrun_providers import get_llm_provider


def resolve_inputs(
    natural: Optional[str] = None,
    seed: Optional[str] = None,
    goal: Optional[str] = None,
    budget: Optional[float] = None,
    candidates: Optional[int] = None,
) -> tuple[str, str, float, int]:
    """Return (seed_sequence, goal, budget, candidate_count) with defaults applied."""
    if natural:
        parsed = get_llm_provider().parse_request(natural)
        seed = seed or parsed.get("seed_sequence")
        goal = goal or parsed.get("goal")
        budget = budget if budget is not None else parsed.get("budget")
        candidates = candidates or parsed.get("candidate_count")

    seed = (seed or DEMO_SEED).strip().upper()
    goal = goal or DEMO_GOAL
    budget = float(budget if budget is not None else DEMO_BUDGET)
    candidates = int(candidates or DEMO_CANDIDATES)
    # clamp candidate count to a sane range for the demo
    candidates = max(4, min(40, candidates))
    return seed, goal, budget, candidates
