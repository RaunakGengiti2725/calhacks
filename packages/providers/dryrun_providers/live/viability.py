"""Live sequence-fitness provider — Evo 2 sequence-likelihood via NVIDIA NIM.

Evo 2 (`arc/evo2-40b`) scores how likely a biological sequence is; we use that
as the viability signal. The external request + response parse is isolated in
`_score_request`; verify it against the current NVIDIA NIM Evo 2 reference (the
schema is evolving) — only that function should need changing. Falls back to the
deterministic mock scorer on any error / missing key, so the cascade is robust.
"""

from __future__ import annotations

import logging
import os

import requests

from dryrun_providers.base import ViabilityProvider
from dryrun_providers.mock.viability import MockViabilityProvider

logger = logging.getLogger("dryrun.live.viability")


class LiveViabilityProvider(ViabilityProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("NVIDIA_API_KEY")
        if not self._api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        self._base = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._model = os.getenv("EVO2_MODEL", "arc/evo2-40b")
        self._mock = MockViabilityProvider()

    def _score_request(self, sequences: list[str]) -> list[float]:
        """ISOLATED external request + parse. Returns one log-likelihood per sequence."""
        resp = requests.post(
            f"{self._base}/biology/arc/evo2-40b/forward",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"sequences": sequences, "output_scores": True},
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        # Expected: a per-sequence score under one of these keys.
        for key in ("scores", "logits", "log_likelihoods", "data"):
            if isinstance(body, dict) and key in body:
                vals = body[key]
                if isinstance(vals, list) and len(vals) == len(sequences):
                    return [float(v) for v in vals]
        raise ValueError("could not parse per-sequence scores from Evo 2 response")

    def score(self, sequences: list[str]) -> list[float]:
        if not sequences:
            return []
        try:
            return self._score_request(sequences)
        except Exception as exc:  # noqa: BLE001 — graceful fallback
            logger.warning("Evo 2 NIM scoring failed (%s); using mock", exc)
            return self._mock.score(sequences)
