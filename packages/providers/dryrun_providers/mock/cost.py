"""Mock cost-data provider: realistic default vendor pricing, no network."""

from __future__ import annotations

from dryrun_core.cost_model import PricingParams
from dryrun_providers.base import CostDataProvider


class MockCostDataProvider(CostDataProvider):
    """Returns realistic default gene-synthesis pricing (~$0.09/bp + cloning fee)."""

    def pricing(self) -> PricingParams:
        return PricingParams()
