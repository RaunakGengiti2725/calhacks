"""Phase 0 smoke tests: the contracts import and instantiate cleanly, with no network."""

from __future__ import annotations

from dryrun_core.cost_model import PricingParams
from dryrun_core.models import (
    Design,
    Mutation,
    ScoredDesign,
    ViabilityScore,
)
from dryrun_core.models import CostEstimate


def test_models_import_and_construct() -> None:
    design = Design(id="d1", sequence="MKTAYIAK", goal="improve thermal stability")
    assert design.length == 8
    assert design.mutation_positions == []


def test_mutation_str() -> None:
    assert str(Mutation(position=23, wild_type="A", variant="V")) == "A23V"


def test_scored_design_round_trips() -> None:
    sd = ScoredDesign(
        design=Design(id="d1", sequence="MKTAYIAK"),
        viability=ViabilityScore(design_id="d1", score=0.8, raw=1.2),
        cost=CostEstimate(
            design_id="d1",
            dna_length_bp=24,
            gc_content=0.5,
            repeat_fraction=0.0,
            complexity_surcharge=0.0,
            base_cost=2.16,
            cloning_fee=75.0,
            total_cost=77.16,
        ),
        embedding=[0.1, 0.2, 0.3],
        success_probability=0.6,
        passed_viability=True,
    )
    assert sd.id == "d1"
    assert sd.fold_confidence is None
    # pydantic round-trip
    assert ScoredDesign.model_validate(sd.model_dump()).id == "d1"


def test_pricing_params_defaults() -> None:
    p = PricingParams()
    assert p.per_bp_usd == 0.09
    assert p.currency == "USD"


def test_provider_contract_surface() -> None:
    from dryrun_providers.base import required_methods

    methods = required_methods()
    assert methods["ViabilityProvider"] == ["score"]
    assert "predict" in methods["StructureProvider"]
