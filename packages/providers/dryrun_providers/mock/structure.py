"""Mock fold-risk (structure) provider.

Returns a real bundled protein structure (crambin, PDB 1CRN — small, public-domain)
as the predicted fold, with synthetic-but-plausible per-residue pLDDT written into
the B-factor column so the frontend colors it exactly like a real AlphaFold model.

The confidence profile is deterministic per sequence and includes a deliberate
LOW-CONFIDENCE LOOP (the demo's "fragile loop"). A design whose mutations land in
that loop is flagged as likely-misfolding — this is what makes the expensive fold
filter actually drop candidates, and it ties the fold risk to specific mutations.

This predicts *structure + confidence*, not thermal stability; low confidence /
disorder is used as a structural-risk signal only.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib.resources import files

import numpy as np

from dryrun_core.models import StructureResult
from dryrun_providers.base import StructureProvider
from dryrun_providers.pdb_utils import extract_sequence, residue_keys, set_plddt

# 1-indexed residue range deliberately modeled as a fragile, low-confidence loop.
FRAGILE_LOOP = (18, 23)
# Surface positions that tolerate stabilizing substitution well — mutations here
# fold a touch more confidently (used to model the "conservative-surface" strategy
# as the genuinely strongest one).
STABILIZING_POSITIONS = frozenset({10, 28, 40})
_STABILIZING_BONUS_PER = 6.0
_STABILIZING_BONUS_CAP = 18.0
_DISORDER_PLDDT = 50.0
_MISFOLD_MEAN_PLDDT = 70.0


@lru_cache(maxsize=1)
def _scaffold() -> tuple[str, int]:
    """Load the bundled crambin PDB once; return (pdb_text, residue_count)."""
    pdb_text = (
        files("dryrun_providers.mock").joinpath("assets", "1crn.pdb").read_text(encoding="utf-8")
    )
    n_res = len(residue_keys(pdb_text))
    return pdb_text, n_res


def scaffold_sequence() -> str:
    """The wild-type sequence of the bundled scaffold (crambin)."""
    pdb_text, _ = _scaffold()
    return extract_sequence(pdb_text)


def _seed_int(sequence: str) -> int:
    return int(hashlib.md5(sequence.encode()).hexdigest()[:8], 16)


def _synthetic_plddt(
    sequence: str, n_res: int, fragile_extra: float, stabilizing_bonus: float
) -> np.ndarray:
    """Plausible per-residue pLDDT: high core, low termini, a fragile loop dip."""
    rng = np.random.RandomState(_seed_int(sequence))
    plddt = np.full(n_res, 88.0 + stabilizing_bonus) + rng.normal(0.0, 3.0, n_res)
    # Termini are typically less confident.
    for i in range(min(3, n_res)):
        plddt[i] -= (3 - i) * 5.0
        plddt[n_res - 1 - i] -= (3 - i) * 5.0
    # The deliberate fragile loop dips low (deeper if mutations land there).
    start, end = FRAGILE_LOOP
    for r in range(start, min(end, n_res) + 1):
        idx = r - 1
        if 0 <= idx < n_res:
            plddt[idx] = 42.0 - fragile_extra + rng.normal(0.0, 3.0)
    return np.clip(plddt, 5.0, 99.0)


def _low_confidence_regions(plddt: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous 1-indexed runs below the disorder threshold."""
    regions: list[tuple[int, int]] = []
    start: int | None = None
    for i, v in enumerate(plddt):
        if v < _DISORDER_PLDDT and start is None:
            start = i + 1
        elif v >= _DISORDER_PLDDT and start is not None:
            regions.append((start, i))
            start = None
    if start is not None:
        regions.append((start, len(plddt)))
    return regions


def _mutation_positions(sequence: str) -> list[int]:
    """Positions where the variant differs from the scaffold wild type."""
    wt = scaffold_sequence()
    return [i + 1 for i, (a, b) in enumerate(zip(wt, sequence)) if a != b]


class MockStructureProvider(StructureProvider):
    def predict(self, design_id: str, sequence: str) -> StructureResult:
        pdb_text, n_res = _scaffold()
        seq = sequence.strip().upper()

        mutated = _mutation_positions(seq)
        start, end = FRAGILE_LOOP
        mutations_in_loop = [p for p in mutated if start <= p <= end]
        # Mutations in the fragile loop deepen the confidence dip.
        fragile_extra = 12.0 * len(mutations_in_loop)
        # Mutations at tolerant stabilizing positions fold a touch more confidently.
        stabilizing_bonus = min(
            _STABILIZING_BONUS_CAP,
            _STABILIZING_BONUS_PER * len(STABILIZING_POSITIONS.intersection(mutated)),
        )

        plddt = _synthetic_plddt(seq, n_res, fragile_extra, stabilizing_bonus)
        mean_plddt = float(plddt.mean())
        min_plddt = float(plddt.min())
        regions = _low_confidence_regions(plddt)
        misfold = bool(mutations_in_loop) or mean_plddt < _MISFOLD_MEAN_PLDDT

        pdb_with_conf = set_plddt(pdb_text, [float(x) for x in plddt])

        return StructureResult(
            design_id=design_id,
            pdb=pdb_with_conf,
            plddt=[round(float(x), 2) for x in plddt],
            mean_plddt=mean_plddt,
            min_plddt=min_plddt,
            low_confidence_regions=regions,
            misfold_flag=misfold,
            method="mock",
            source="bundled-pdb:1CRN(crambin)",
        )
