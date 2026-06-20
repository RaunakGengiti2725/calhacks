"""Mock design-generator provider.

Stands in for the Evo 2 generative endpoint. Produces N candidate variants of the
seed by applying realistic point mutations. Crucially, variants are generated in
"strategy families" — each family targets a different region with a characteristic
substitution style — so the candidate pool has genuine structure: tight clusters
of near-identical designs (which naive top-N over-selects) spread across distinct
regions of sequence space (which the DryRun optimizer diversifies over).

Fully deterministic: the same (seed, goal, n) always yields the same variants.
"""

from __future__ import annotations

import hashlib
import random

from dryrun_core.models import Design, Mutation
from dryrun_providers.base import GenerationProvider

# Each family: a region (1-indexed positions), a pool of substitution residues,
# a relative weight (how many variants), and a short label.
# Positions/pools are tuned for the 46-residue crambin demo scaffold but degrade
# gracefully for any seed (positions are clamped to the sequence length).
# Pools use residues of similar natural frequency so each family's viability is
# uniform (tight clusters). Each family's positions are chosen so the seed residue
# there is NOT in the family's pool (so every member mutates by the same count —
# no effective-mutation-count variance). The tempting family's edge comes from
# STRUCTURE: it mutates positions that fold more confidently (see structure
# provider's STABILIZING_POSITIONS), which the mock controls precisely. Families
# occupy distinct, non-overlapping regions. (Crambin 1CRN scaffold residues:
# ...R10,S11,...T28...C40 for cons; F13,G31,Y44 for core; etc.)
_FAMILIES: list[dict] = [
    # Conservative substitutions at tolerant, well-folding surface positions
    # (incl. removing a rare buried Cys at 40) — the genuinely strongest, tightest
    # "tempting cluster" that naive top-N over-selects.
    {"label": "conservative-surface", "positions": [10, 28, 40], "pool": "AL", "weight": 5},
    # Hydrophobic core repacking — buildable, distinct region; lower-scoring than
    # the tempting cluster, a region DryRun diversifies into.
    {"label": "core-repack", "positions": [13, 31, 44], "pool": "IV", "weight": 3},
    # Surface charge engineering at common positions — buildable, distinct region.
    {"label": "charge-surface", "positions": [11, 17, 30], "pool": "EK", "weight": 3},
    # Loop rigidification — swaps structurally-critical prolines in the loop for
    # common residues, so it scores HIGH on the cheap viability filter (passes it
    # easily) yet MISFOLDS, and is caught only by the expensive fold step. This is
    # exactly why the fold step earns its cost.
    {"label": "loop-rigidify", "positions": [19, 21, 23], "pool": "L", "weight": 2},
    # Destabilizing substitutions to the rarest residue — low plausibility, caught
    # by the cheap viability filter before any expensive folding is spent on them.
    {"label": "destabilizing", "positions": [2, 8, 14, 24, 34, 42], "pool": "W", "weight": 3},
]


def _seed_int(*parts: str) -> int:
    h = hashlib.md5("||".join(parts).encode()).hexdigest()
    return int(h[:8], 16)


def _apply(seq: list[str], pos: int, aa: str, mutations: list[Mutation]) -> None:
    """Apply a 1-indexed substitution in place, recording it (only if it changes)."""
    idx = pos - 1
    if 0 <= idx < len(seq) and seq[idx] != aa:
        mutations.append(Mutation(position=pos, wild_type=seq[idx], variant=aa))
        seq[idx] = aa


class MockGenerationProvider(GenerationProvider):
    def generate(self, seed_sequence: str, goal: str, n: int) -> list[Design]:
        seed = seed_sequence.strip().upper()
        if not seed or n <= 0:
            return []
        rng = random.Random(_seed_int(seed, goal or "", str(n)))

        # Distribute n variants across families by weight (at least 1 each if room).
        total_weight = sum(f["weight"] for f in _FAMILIES)
        counts = [max(1, round(n * f["weight"] / total_weight)) for f in _FAMILIES]
        # trim/pad to exactly n
        while sum(counts) > n:
            counts[counts.index(max(counts))] -= 1
        while sum(counts) < n:
            counts[counts.index(min(counts))] += 1

        designs: list[Design] = []
        for fam, k in zip(_FAMILIES, counts):
            positions = [p for p in fam["positions"] if p <= len(seed)]
            for v in range(k):
                residues = list(seed)
                mutations: list[Mutation] = []
                # Within-family variation comes from independently sampling each
                # signature position from the family's residue pool — so members
                # stay near-identical (a tight cluster) without touching other
                # regions (which would contaminate the fold signal).
                for p in positions:
                    aa = rng.choice(fam["pool"])
                    _apply(residues, p, aa, mutations)

                variant_seq = "".join(residues)
                designs.append(
                    Design(
                        id=f"{fam['label'][:4]}-{len(designs):02d}",
                        sequence=variant_seq,
                        parent_sequence=seed,
                        goal=goal,
                        mutations=mutations,
                        generation_method=f"mock-point-mutation:{fam['label']}",
                    )
                )
        return designs
