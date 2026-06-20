"""Shared test helpers for the core suite."""

from __future__ import annotations

from dryrun_core.models import CostEstimate, Design, ScoredDesign, ViabilityScore


def make_scored(
    design_id: str,
    p: float,
    cost: float,
    embedding: list[float],
    sequence: str = "MKKLLAVIG",
) -> ScoredDesign:
    """Construct a ScoredDesign with explicit p / cost / embedding for optimizer tests."""
    return ScoredDesign(
        design=Design(id=design_id, sequence=sequence),
        viability=ViabilityScore(design_id=design_id, score=p, raw=p),
        cost=CostEstimate(
            design_id=design_id,
            dna_length_bp=len(sequence) * 3 + 3,
            gc_content=0.5,
            repeat_fraction=0.0,
            complexity_surcharge=0.0,
            base_cost=max(0.0, cost - 75.0),
            cloning_fee=75.0,
            total_cost=cost,
        ),
        embedding=list(embedding),
        success_probability=p,
        passed_viability=True,
        passed_fold=True,
    )
