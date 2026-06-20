"""Provider abstraction layer — the heart of the prime directive.

Every external service is reached through one of these ABCs. Each has a Mock
implementation (instant synthetic data, no network) and a Live implementation
(real API). `DRYRUN_MODE` selects which, globally, via the factory.

Business logic NEVER calls an external API directly — it calls one of these
interfaces. Live implementations isolate each external request in one small
parsing function so a changed API schema is a one-function fix.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dryrun_core.cost_model import PricingParams
from dryrun_core.models import Design, StructureResult


class LLMProvider(ABC):
    """The conversational/reasoning LLM (ASI:One in live mode).

    Standalone use in the orchestrator: parse a researcher's plain-English
    request into structured fields, and write the plain-English report summary.
    """

    @abstractmethod
    def parse_request(self, text: str) -> dict:
        """Extract {seed_sequence, goal, budget, candidate_count} from free text.

        Returns a dict with those keys (values may be None if not present);
        callers apply defaults.
        """

    @abstractmethod
    def summarize(self, report_facts: dict) -> str:
        """Write a short plain-English summary from already-computed report facts.

        Must only narrate facts passed in — never invent numbers.
        """


class GenerationProvider(ABC):
    """Proposes N candidate variants of a seed toward a design goal.

    Live mode: Evo 2 NIM generative endpoint. Mock mode: realistic point
    mutations. (Added alongside the four named ABCs because variant generation
    is a distinct external capability from viability scoring, even though both
    map to Evo 2 in live mode.)
    """

    @abstractmethod
    def generate(self, seed_sequence: str, goal: str, n: int) -> list[Design]:
        """Return N candidate Designs derived from the seed toward the goal."""


class ViabilityProvider(ABC):
    """Scores how biologically plausible each sequence is (the cheap first pass).

    Live mode: Evo 2 NIM sequence-likelihood scoring. Mock mode: deterministic
    pseudo-scores from sequence features.
    """

    @abstractmethod
    def score(self, sequences: list[str]) -> list[float]:
        """Return one raw viability score per input sequence (order preserved)."""


class StructureProvider(ABC):
    """Predicts 3D structure + per-residue confidence (the expensive step).

    Live mode: AlphaFold2 NIM predict-structure-from-sequence. Mock mode: a
    bundled real PDB with synthetic-but-plausible pLDDT incl. a fragile region.
    """

    @abstractmethod
    def predict(self, design_id: str, sequence: str) -> StructureResult:
        """Predict structure + confidence for one sequence."""


class CostDataProvider(ABC):
    """Supplies the synthesis pricing parameters the cost model is anchored to.

    The cost MODEL (length/GC/repeat/complexity math) lives in
    `dryrun_core.cost_model`; this provider supplies the vendor-specific rates.
    Live mode is where a real vendor pricing API attaches.
    """

    @abstractmethod
    def pricing(self) -> PricingParams:
        """Return the current pricing parameters."""


def required_methods() -> dict[str, list[str]]:
    """Introspection helper used by tests to assert the contract is complete."""
    return {
        "LLMProvider": ["parse_request", "summarize"],
        "GenerationProvider": ["generate"],
        "ViabilityProvider": ["score"],
        "StructureProvider": ["predict"],
        "CostDataProvider": ["pricing"],
    }


__all__ = [
    "LLMProvider",
    "GenerationProvider",
    "ViabilityProvider",
    "StructureProvider",
    "CostDataProvider",
    "PricingParams",
    "required_methods",
]
