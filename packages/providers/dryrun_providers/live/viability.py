"""Live sequence-fitness provider — Evo 2 DNA likelihood via NVIDIA NIM.

Evo 2 is a genomic model, so "how plausible is this protein" becomes "how likely is
its coding DNA under Evo 2". We back-translate each protein to DNA, run Evo 2's
`forward` pass to get per-position logits, and compute the mean teacher-forced
log-likelihood of the actual bases — a real sequence-likelihood viability signal.

The external request + NPZ unpack + likelihood math is isolated in `_score_one`;
verify the `output_layers` name and logits shape against your NIM (the forward
response is a base64 NumPy NPZ — schema documented but evolving). On any error /
missing key the whole batch falls back to the deterministic mock scorer so the
viability scores stay on one consistent scale, and the fallback is recorded in
`provenance` so it is never shown as a real Evo 2 result.

Endpoint reference (hosted): POST {base}/biology/arc/evo2-40b/forward
  request : {"sequence": <DNA>, "output_layers": ["output_layer"]}
  response: {"data": <base64 NPZ with a [seq_len, *, vocab] logits array>}
See https://docs.nvidia.com/nim/bionemo/evo2/latest/endpoints.html
"""

from __future__ import annotations

import base64
import io
import logging
import math
import os

import numpy as np
import requests

from dryrun_providers import provenance
from dryrun_providers.base import ViabilityProvider
from dryrun_providers.config import is_strict
from dryrun_providers.live._dna import protein_to_dna
from dryrun_providers.mock.viability import MockViabilityProvider

logger = logging.getLogger("dryrun.live.viability")

_STAGE = "viability"
_DEFAULT_BASE = "https://health.api.nvidia.com/v1"
# Evo 2 tokenizes DNA as raw ASCII bytes; the logits vocab is the (padded) byte
# space, so a base's target index is simply its ASCII code.
_VOCAB = 512


def _logits_from_npz(raw_b64: str) -> np.ndarray:
    """Decode the base64 NPZ and return the [seq_len, vocab] logits array."""
    buf = io.BytesIO(base64.b64decode(raw_b64.encode("ascii")))
    npz = np.load(buf, allow_pickle=False)
    # Pick the array whose trailing dimension is the (padded byte) vocab.
    for key in npz.files:
        arr = np.asarray(npz[key], dtype=np.float64)
        if arr.ndim >= 2 and arr.shape[-1] == _VOCAB:
            return arr.reshape(-1, _VOCAB)  # collapse any batch dim -> [seq_len, vocab]
    raise ValueError("no [*, vocab] logits array in Evo 2 forward NPZ")


def _mean_log_likelihood(dna: str, logits: np.ndarray) -> float:
    """Mean teacher-forced log-prob of each next base under the model's logits."""
    n = min(len(dna) - 1, logits.shape[0] - 1)
    if n <= 0:
        raise ValueError("sequence too short to score")
    total = 0.0
    for i in range(n):
        row = logits[i]
        row = row - row.max()  # numerical-stable log-softmax
        log_z = math.log(float(np.exp(row).sum()))
        target = ord(dna[i + 1])
        if target >= row.shape[0]:
            raise ValueError("base token id outside logits vocab")
        total += float(row[target]) - log_z
    return total / n


class LiveViabilityProvider(ViabilityProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("NVIDIA_API_KEY")
        if not self._api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        self._base = os.getenv("NVIDIA_NIM_BASE_URL", _DEFAULT_BASE).rstrip("/")
        self._model = os.getenv("EVO2_MODEL", "arc/evo2-40b")
        self._mock = MockViabilityProvider()

    def _score_one(self, protein: str) -> float:
        """ISOLATED external request + parse → one mean log-likelihood for a protein."""
        dna = protein_to_dna(protein)
        if len(dna) < 6:
            raise ValueError("protein too short to back-translate/score")
        resp = requests.post(
            f"{self._base}/biology/arc/evo2-40b/forward",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"sequence": dna, "output_layers": ["output_layer"]},
            timeout=120,
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, str):
            raise ValueError("no base64 'data' in Evo 2 forward response")
        return _mean_log_likelihood(dna, _logits_from_npz(data))

    def score(self, sequences: list[str]) -> list[float]:
        if not sequences:
            return []
        try:
            scores = [self._score_one(s.strip().upper()) for s in sequences]
            provenance.mark(_STAGE, provenance.LIVE, "evo2-nim forward log-likelihood")
            return scores
        except Exception as exc:  # noqa: BLE001 — graceful fallback unless strict
            if is_strict():
                raise
            logger.warning("Evo 2 NIM scoring failed (%s); using mock", exc)
            provenance.mark(_STAGE, provenance.FALLBACK, str(exc))
            return self._mock.score(sequences)
