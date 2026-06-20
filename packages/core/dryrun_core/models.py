"""Domain models for DryRun.

These are the typed contracts that flow through the whole cascade:
generate -> score viability -> fold-risk (survivors only) -> cost -> optimize -> report.

Pure data only. This module imports nothing outside pydantic/stdlib so the core
stays a leaf dependency that providers, agents, and the API can all build on.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class Mutation(BaseModel):
    """A single point mutation relative to the seed/wild-type sequence.

    `position` is 1-indexed (residue 1 is the first amino acid), matching the
    convention biologists and PDB files use.
    """

    position: int
    wild_type: str
    variant: str

    def __str__(self) -> str:  # e.g. "A23V"
        return f"{self.wild_type}{self.position}{self.variant}"


class Design(BaseModel):
    """A candidate protein design (an amino-acid sequence)."""

    id: str
    sequence: str
    parent_id: Optional[str] = None
    parent_sequence: Optional[str] = None
    goal: Optional[str] = None
    mutations: list[Mutation] = Field(default_factory=list)
    generation_method: str = "mock"
    is_wild_type: bool = False

    @property
    def length(self) -> int:
        return len(self.sequence)

    @property
    def mutation_positions(self) -> list[int]:
        return [m.position for m in self.mutations]


# ---------------------------------------------------------------------------
# Per-stage results
# ---------------------------------------------------------------------------


class ViabilityScore(BaseModel):
    """Cheap, whole-pool first-pass: a normalized proxy for biological plausibility."""

    design_id: str
    score: float  # normalized 0..1 (higher = more plausible)
    raw: float  # provider-native score before normalization
    method: str = "mock"


class StructureResult(BaseModel):
    """Structure prediction + per-residue confidence for one design.

    NOTE: This predicts *structure* and *confidence* (pLDDT), not thermal
    stability directly. Low confidence and predicted disorder are used as a
    structural-risk signal, not as a stability oracle.
    """

    design_id: str
    pdb: str  # full PDB file text
    plddt: list[float]  # per-residue confidence, 0..100 (AlphaFold scale)
    mean_plddt: float
    min_plddt: float
    # 1-indexed inclusive residue ranges flagged as structurally fragile.
    low_confidence_regions: list[tuple[int, int]] = Field(default_factory=list)
    misfold_flag: bool = False
    method: str = "mock"
    source: str = "bundled-pdb"
    note: str = (
        "Predicts structure and per-residue confidence (pLDDT), not thermal "
        "stability. Low confidence / disorder is a risk signal, not a stability oracle."
    )


class CostEstimate(BaseModel):
    """Estimated synthesis-plus-cloning cost for one construct."""

    design_id: str
    dna_length_bp: int
    gc_content: float
    repeat_fraction: float
    complexity_surcharge: float  # multiplier applied for hard-to-synthesize features
    base_cost: float  # per-bp synthesis cost
    cloning_fee: float  # flat per-construct cloning/assembly fee
    total_cost: float
    currency: str = "USD"


class ScoredDesign(BaseModel):
    """A design carried through the full cascade with all derived signals.

    This is the unit the portfolio optimizer consumes: it needs a success
    probability `p_i`, a synthesis cost `c_i`, and an embedding for diversity.
    `structure` is only populated for designs that survived the viability filter
    (the expensive fold step runs on survivors only).
    """

    design: Design
    viability: ViabilityScore
    structure: Optional[StructureResult] = None
    cost: CostEstimate
    embedding: list[float]
    success_probability: float  # p_i in [0, 1]
    passed_viability: bool = False
    passed_fold: bool = False

    @property
    def id(self) -> str:
        return self.design.id

    @property
    def fold_confidence(self) -> Optional[float]:
        return self.structure.mean_plddt if self.structure else None


# ---------------------------------------------------------------------------
# Optimizer output
# ---------------------------------------------------------------------------


class Portfolio(BaseModel):
    """A selected subset of designs under a budget, plus its headline metrics."""

    method: str  # "submodular" | "naive_topn"
    selected_ids: list[str]
    budget: float
    total_cost: float
    expected_successes: float  # sum of p_i over the selection
    expected_distinct_successes: float  # submodular coverage value (diversity-aware)
    cost_per_success: float
    count: int


class PortfolioComparison(BaseModel):
    """The DryRun-optimized portfolio vs the naive top-N at the same budget."""

    optimized: Portfolio
    naive: Portfolio
    expected_successes_uplift: float  # optimized.expected_distinct - naive.expected_distinct
    # Extra dollars the naive ordering would need to match DryRun's expected
    # distinct successes (None if naive already matches or estimate unavailable).
    dollars_naive_needs_to_match: Optional[float] = None


# ---------------------------------------------------------------------------
# Report payload (what the Reporting agent emits and the frontend renders)
# ---------------------------------------------------------------------------


class FunnelCounts(BaseModel):
    """Screening-cascade counts: the cheap filter runs on the whole pool, the
    expensive fold filter only on survivors."""

    generated: int
    viability_passed: int
    fold_passed: int
    selected: int


class SequenceSpacePoint(BaseModel):
    """One candidate projected to 2D for the diversity scatter."""

    design_id: str
    x: float
    y: float
    selected_optimized: bool
    selected_naive: bool
    success_probability: float


class CandidateRow(BaseModel):
    """One row of the per-candidate table."""

    design_id: str
    sequence_preview: str
    viability: float
    fold_confidence: Optional[float]
    cost: float
    success_probability: float
    selected: bool  # selected by DryRun optimizer
    selected_naive: bool
    mutations: list[str]


class StructurePayload(BaseModel):
    """Structure + confidence track for a single design, ready for Mol* + the 1D heatmap."""

    design_id: str
    is_wild_type: bool
    pdb: str
    plddt: list[float]
    mean_plddt: float
    low_confidence_regions: list[tuple[int, int]]
    mutation_positions: list[int]
    misfold_flag: bool


class ReportSummary(BaseModel):
    """The headline metric row."""

    designs_selected: int
    designs_total: int
    spend: float
    budget: float
    expected_successes: float
    cost_per_success: float
    naive_expected_successes: float
    uplift_ratio: float  # optimized / naive expected distinct successes


class ReportMeta(BaseModel):
    mode: str  # "mock" | "live"
    goal: Optional[str]
    seed_sequence: str
    seed_length: int
    candidate_count: int
    budget: float
    generated_at: str


class Report(BaseModel):
    """The single, complete, well-typed payload the frontend renders directly."""

    summary: ReportSummary
    funnel: FunnelCounts
    comparison: PortfolioComparison
    candidates: list[CandidateRow]
    sequence_space: list[SequenceSpacePoint]
    structures: list[StructurePayload]
    wild_type_structure: Optional[StructurePayload] = None
    plain_summary: str
    meta: ReportMeta
