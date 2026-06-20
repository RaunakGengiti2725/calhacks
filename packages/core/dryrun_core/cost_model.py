"""Synthesis-plus-cloning cost estimation.

`PricingParams` is the vendor-rate contract (supplied by a CostDataProvider).
The cost MODEL math (length / GC / repeat / complexity) is implemented here in
Phase 1 and takes a PricingParams as input, so core never depends on providers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PricingParams:
    """Vendor pricing parameters the cost model is anchored to.

    Defaults reflect a realistic gene-synthesis market (~$0.09 per base pair
    plus a flat per-construct cloning/assembly fee).
    """

    per_bp_usd: float = 0.09
    cloning_fee_usd: float = 75.0
    # Surcharge multipliers for hard-to-synthesize features.
    extreme_gc_surcharge: float = 0.35  # added when GC content is far from ideal
    repeat_surcharge: float = 0.50  # added at maximal repeat content
    # GC content is "ideal" near this fraction; deviation drives the surcharge.
    ideal_gc: float = 0.50
    currency: str = "USD"
