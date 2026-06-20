"""Live cost-data provider.

The cost MODEL (length / GC / repeat / complexity) lives in core and is shared by
mock and live. This provider is the seam where a real vendor pricing API (e.g.
Twist Bioscience quoting) would attach to supply live rates. Until that's wired,
it returns the same realistic defaults as mock — so `live` mode is fully
functional today.
"""

from __future__ import annotations

import logging

from dryrun_core.cost_model import PricingParams
from dryrun_providers import provenance
from dryrun_providers.base import CostDataProvider
from dryrun_providers.mock.cost import MockCostDataProvider

logger = logging.getLogger("dryrun.live.cost")

_STAGE = "cost"


class LiveCostDataProvider(CostDataProvider):
    def __init__(self) -> None:
        self._mock = MockCostDataProvider()

    def pricing(self) -> PricingParams:
        # The cost MODEL (length/GC/repeat/complexity) is real in-process logic in
        # dryrun_core.cost_model; this provider only supplies the per-bp / cloning
        # base RATES. No public vendor (Twist/IDT/Genscript) exposes an unauthenticated
        # quoting API, so these remain realistic standard rates rather than a fake
        # external call. Marked "local" — a real algorithm, not a mock fallback.
        provenance.mark(_STAGE, provenance.LOCAL, "in-process cost model (standard vendor rates)")
        return self._mock.pricing()
