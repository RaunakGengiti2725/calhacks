"""Live design-generator provider — Evo 2 generative via NVIDIA NIM.

Proposes candidate variants with the Evo 2 generative endpoint. The external
request + parse is isolated in `_generate_request`; verify it against the current
NVIDIA NIM Evo 2 reference. Falls back to the mock point-mutation generator on any
error / missing key (which also guarantees variants are valid amino-acid strings
the rest of the cascade can consume).
"""

from __future__ import annotations

import logging
import os

import requests

from dryrun_core.models import Design, Mutation
from dryrun_providers.base import GenerationProvider
from dryrun_providers.mock.generation import MockGenerationProvider

logger = logging.getLogger("dryrun.live.generation")

_AA = set("ACDEFGHIKLMNPQRSTVWY")


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
        self._base = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._model = os.getenv("EVO2_MODEL", "arc/evo2-40b")
        self._mock = MockGenerationProvider()

    def _generate_request(self, seed: str, goal: str, n: int) -> list[str]:
        """ISOLATED external request + parse. Returns a list of variant sequences."""
        resp = requests.post(
            f"{self._base}/biology/arc/evo2-40b/generate",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"sequence": seed, "num_samples": n, "temperature": 0.7},
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        seqs: list[str] = []
        candidates = body.get("sequences") or body.get("samples") or body.get("data") or []
        for item in candidates:
            s = item if isinstance(item, str) else item.get("sequence", "")
            s = "".join(c for c in s.strip().upper() if c in _AA)
            if s:
                seqs.append(s)
        if not seqs:
            raise ValueError("no usable variant sequences in Evo 2 response")
        return seqs

    def generate(self, seed_sequence: str, goal: str, n: int) -> list[Design]:
        seed = seed_sequence.strip().upper()
        try:
            variants = self._generate_request(seed, goal, n)
            designs: list[Design] = []
            for i, v in enumerate(variants[:n]):
                # only diff against the seed when lengths match (point variants)
                muts = _diff_mutations(seed, v) if len(v) == len(seed) else []
                designs.append(
                    Design(
                        id=f"evo2-{i:02d}",
                        sequence=v,
                        parent_sequence=seed,
                        goal=goal,
                        mutations=muts,
                        generation_method="evo2-nim",
                    )
                )
            if not designs:
                raise ValueError("Evo 2 returned no designs")
            return designs
        except Exception as exc:  # noqa: BLE001 — graceful fallback
            logger.warning("Evo 2 NIM generation failed (%s); using mock", exc)
            return self._mock.generate(seed_sequence, goal, n)
