"""Combine sequence viability + structural confidence into a success probability p_i.

p_i is the estimate the portfolio optimizer treats as "probability this construct
yields a usable, well-folded protein if synthesized." It is intentionally
transparent and monotone:

  * higher viability (biological plausibility) -> higher p
  * higher mean pLDDT (structural confidence) -> higher p
  * predicted disorder (low-pLDDT residues) and a misfold flag -> lower p

This is a calibratable heuristic, not a validated oracle (see Phase 6:
calibration against real experimental outcomes). All weights are named constants.
"""

from __future__ import annotations

from typing import Optional

from dryrun_core.models import StructureResult

# Weights for the viability/structure blend (sum to 1).
W_VIABILITY = 0.45
W_STRUCTURE = 0.55

# A design that passed viability but was not folded (live folding is capped) is
# discounted: it has no structural confirmation.
NO_STRUCTURE_FACTOR = 0.60

# A design flagged as likely-misfolding is penalized.
MISFOLD_PENALTY = 0.60

# pLDDT below this is treated as disordered/low-confidence.
DISORDER_PLDDT = 50.0

# Clamp p into a believable band (never 0 or 1).
P_MIN = 0.02
P_MAX = 0.98


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def structure_term(structure: StructureResult) -> float:
    """Map a structure result to a [0, 1] structural-confidence term."""
    conf = _clamp01(structure.mean_plddt / 100.0)
    n = len(structure.plddt) or 1
    disorder_fraction = sum(1 for x in structure.plddt if x < DISORDER_PLDDT) / n
    return _clamp01(conf * (1.0 - 0.5 * disorder_fraction))


def success_probability(
    viability_score: float, structure: Optional[StructureResult]
) -> float:
    """Compute p_i in [P_MIN, P_MAX] from viability and (optional) structure."""
    v = _clamp01(viability_score)
    if structure is None:
        p = v * NO_STRUCTURE_FACTOR
    else:
        s = structure_term(structure)
        p = W_VIABILITY * v + W_STRUCTURE * s
        if structure.misfold_flag:
            p *= MISFOLD_PENALTY
    return max(P_MIN, min(P_MAX, p))


__all__ = [
    "W_VIABILITY",
    "W_STRUCTURE",
    "NO_STRUCTURE_FACTOR",
    "MISFOLD_PENALTY",
    "structure_term",
    "success_probability",
]
