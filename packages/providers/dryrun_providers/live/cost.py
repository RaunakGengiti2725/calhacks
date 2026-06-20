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
from dryrun_providers.base import CostDataProvider
from dryrun_providers.mock.cost import MockCostDataProvider

logger = logging.getLogger("dryrun.live.cost")


class LiveCostDataProvider(CostDataProvider):
    def __init__(self) -> None:
        self._mock = MockCostDataProvider()

    def pricing(self) -> PricingParams:
        # Phase 6: fetch live per-bp / cloning rates from a vendor pricing API and
        # parse them in one isolated function here, falling back to mock on error.
        return self._mock.pricing()
