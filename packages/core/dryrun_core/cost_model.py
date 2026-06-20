"""Synthesis-plus-cloning cost estimation.

`PricingParams` is the vendor-rate contract (supplied by a CostDataProvider).
The cost MODEL math below takes a PricingParams as input, so core never depends
on providers.

The model is a real, defensible estimate (not a guess): it back-translates the
protein to a representative DNA coding sequence, then prices it on construct
length, GC content, and repeat content — the three features gene-synthesis
vendors actually surcharge for — anchored to a realistic ~$0.09/bp + flat
cloning fee.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from dryrun_core.models import CostEstimate


@dataclass(frozen=True)
class PricingParams:
    """Vendor pricing parameters the cost model is anchored to.

    Defaults reflect a realistic gene-synthesis market (~$0.09 per base pair
    plus a flat per-construct cloning/assembly fee).
    """

    per_bp_usd: float = 0.09
    cloning_fee_usd: float = 75.0
    # Surcharge fractions for hard-to-synthesize features (added to base cost).
    extreme_gc_surcharge: float = 0.35  # max added when GC content is far from ideal
    repeat_surcharge: float = 0.50  # max added at maximal repeat content
    ideal_gc: float = 0.50  # GC content is "ideal" near this fraction
    max_gc_deviation: float = 0.20  # |gc - ideal| at/above which surcharge is maxed
    currency: str = "USD"


# Representative high-usage codon per amino acid (E. coli-ish), plus stop.
_CODON: dict[str, str] = {
    "A": "GCG", "R": "CGC", "N": "AAC", "D": "GAC", "C": "TGC", "Q": "CAG",
    "E": "GAA", "G": "GGC", "H": "CAC", "I": "ATC", "L": "CTG", "K": "AAA",
    "M": "ATG", "F": "TTC", "P": "CCG", "S": "AGC", "T": "ACC", "W": "TGG",
    "Y": "TAC", "V": "GTG", "*": "TAA",
}
_REPEAT_K = 10


def back_translate(protein: str) -> str:
    """Most-common-codon back-translation to a representative coding DNA (+ stop)."""
    seq = protein.strip().upper()
    dna = "".join(_CODON.get(aa, "NNN") for aa in seq)
    return dna + _CODON["*"]


def gc_content(dna: str) -> float:
    if not dna:
        return 0.0
    gc = sum(1 for b in dna if b in ("G", "C"))
    return gc / len(dna)


def repeat_fraction(dna: str, k: int = _REPEAT_K) -> float:
    """Fraction of k-mer windows that belong to a k-mer occurring more than once."""
    n_windows = len(dna) - k + 1
    if n_windows <= 1:
        return 0.0
    counts = Counter(dna[i : i + k] for i in range(n_windows))
    duplicated = sum(c for c in counts.values() if c > 1)
    return duplicated / n_windows


def estimate_cost(
    design_id: str, protein_sequence: str, params: PricingParams | None = None
) -> CostEstimate:
    """Estimate the synthesis-plus-cloning cost for one construct."""
    p = params or PricingParams()
    dna = back_translate(protein_sequence)
    dna_len = len(dna)
    gc = gc_content(dna)
    rep = repeat_fraction(dna)

    gc_dev = min(1.0, abs(gc - p.ideal_gc) / p.max_gc_deviation) if p.max_gc_deviation else 0.0
    surcharge_fraction = p.extreme_gc_surcharge * gc_dev + p.repeat_surcharge * rep

    base_cost = p.per_bp_usd * dna_len
    total_cost = base_cost * (1.0 + surcharge_fraction) + p.cloning_fee_usd

    return CostEstimate(
        design_id=design_id,
        dna_length_bp=dna_len,
        gc_content=gc,
        repeat_fraction=rep,
        complexity_surcharge=surcharge_fraction,
        base_cost=base_cost,
        cloning_fee=p.cloning_fee_usd,
        total_cost=total_cost,
        currency=p.currency,
    )


__all__ = [
    "PricingParams",
    "back_translate",
    "gc_content",
    "repeat_fraction",
    "estimate_cost",
]
