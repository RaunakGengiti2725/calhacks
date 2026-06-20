"""Live design-generator provider — Evo 2 generative via NVIDIA NIM.

Evo 2 is a genomic (DNA) model, so this provider bridges protein <-> DNA: it
back-translates the seed protein to DNA, primes Evo 2 with a conserved DNA prefix,
samples a fresh continuation per variant, then translates the result back to a
protein. Each external call is isolated in `_generate_one` (one sample per request,
matching the documented NIM `generate` schema). Falls back to the mock point-
mutation generator on any error / missing key, and records which path ran in
`provenance` so a fallback can never be shown as a real Evo 2 result.

Endpoint reference (hosted): POST {base}/biology/arc/evo2-40b/generate
  request : {"sequence": <DNA>, "num_tokens": int, "temperature": float,
             "top_k": int, "top_p": float, "random_seed": int}
  response: {"sequence": <generated DNA>, ...}
See https://docs.nvidia.com/nim/bionemo/evo2/latest/endpoints.html — verify against
your NIM once you have an NVIDIA key (this path is doc-matched, not yet live-tested).
"""

from __future__ import annotations

import logging
import os

import requests

from dryrun_core.models import Design, Mutation
from dryrun_providers import provenance
from dryrun_providers.base import GenerationProvider
from dryrun_providers.config import is_strict
from dryrun_providers.live._dna import dna_to_protein, protein_to_dna
from dryrun_providers.mock.generation import MockGenerationProvider

logger = logging.getLogger("dryrun.live.generation")

_AA = set("ACDEFGHIKLMNPQRSTVWY")
_STAGE = "generation"
# Hosted NIM base for the biology models. Defaults to the health.* host (where the
# Evo 2 / AlphaFold2 NIMs live), but is overridable for a self-hosted NIM.
_DEFAULT_BASE = "https://health.api.nvidia.com/v1"


def _diff_mutations(seed: str, variant: str) -> list[Mutation]:
    return [
        Mutation(position=i + 1, wild_type=a, variant=b)
        for i, (a, b) in enumerate(zip(seed, variant))
        if a != b
    ]


class LiveGenerationProvider(GenerationProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("NVIDIA_API_KEY")
        if not self._api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        self._base = os.getenv("NVIDIA_NIM_BASE_URL", _DEFAULT_BASE).rstrip("/")
        self._model = os.getenv("EVO2_MODEL", "arc/evo2-40b")
        self._mock = MockGenerationProvider()

    def _generate_one(self, dna_prompt: str, num_tokens: int, random_seed: int) -> str:
        """ISOLATED external request + parse. Returns generated DNA (prompt-joined).

        Evo 2 `generate` produces ONE sample per call. The response `sequence` is
        the generated continuation; we join it onto the prompt so the variant keeps
        the conserved prefix and diverges downstream.
        """
        resp = requests.post(
            f"{self._base}/biology/arc/evo2-40b/generate",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "sequence": dna_prompt,
                "num_tokens": num_tokens,
                "temperature": 0.7,
                "top_k": 4,
                "top_p": 0.95,
                "random_seed": random_seed,
            },
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        gen = body.get("sequence") if isinstance(body, dict) else None
        if not isinstance(gen, str) or not gen.strip():
            raise ValueError("no 'sequence' in Evo 2 generate response")
        gen = "".join(c for c in gen.strip().upper() if c in "ACGT")
        # Some deployments echo the prompt; others return only new tokens. Normalize.
        return gen if gen.startswith(dna_prompt) else dna_prompt + gen

    def generate(self, seed_sequence: str, goal: str, n: int) -> list[Design]:
        seed = seed_sequence.strip().upper()
        try:
            seed_dna = protein_to_dna(seed)
            if not seed_dna:
                raise ValueError("seed has no translatable residues")
            # Keep the first ~half of the protein fixed (a conserved scaffold) and
            # let Evo 2 redesign the remainder.
            prefix_res = max(1, len(seed) // 2)
            prompt = seed_dna[: prefix_res * 3]
            num_tokens = max(3, (len(seed) - prefix_res) * 3)

            designs: list[Design] = []
            for i in range(n):
                variant_dna = self._generate_one(prompt, num_tokens, random_seed=i)
                variant = dna_to_protein(variant_dna)
                variant = "".join(c for c in variant if c in _AA)
                if not variant:
                    continue
                muts = _diff_mutations(seed, variant) if len(variant) == len(seed) else []
                designs.append(
                    Design(
                        id=f"evo2-{i:02d}",
                        sequence=variant,
                        parent_sequence=seed,
                        goal=goal,
                        mutations=muts,
                        generation_method="evo2-nim",
                    )
                )
            if not designs:
                raise ValueError("Evo 2 returned no usable designs")
            provenance.mark(_STAGE, provenance.LIVE, "evo2-nim generate")
            return designs
        except Exception as exc:  # noqa: BLE001 — graceful fallback unless strict
            if is_strict():
                raise
            logger.warning("Evo 2 NIM generation failed (%s); using mock", exc)
            provenance.mark(_STAGE, provenance.FALLBACK, str(exc))
            return self._mock.generate(seed_sequence, goal, n)
