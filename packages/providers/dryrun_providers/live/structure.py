"""Live fold-risk provider — AlphaFold2 via NVIDIA NIM.

Calls the `predict-structure-from-sequence` endpoint, which returns a PDB whose
B-factor column holds per-residue pLDDT; we parse that with the shared pdb_utils
(the one place that knows the PDB column layout). The HTTP request + response
unwrap is isolated in `_predict_pdb` so a changed API schema is a one-function
fix. Falls back to mock on any error / missing key.

Scoping note: full MSA-based AlphaFold2 is slow, so the cascade caps how many
viability survivors are folded (DRYRUN_FOLD_CAP); mock remains the demo default.
"""

from __future__ import annotations

import logging
import os

import requests

from dryrun_core.models import StructureResult
from dryrun_providers.base import StructureProvider
from dryrun_providers.mock.structure import MockStructureProvider
from dryrun_providers.pdb_utils import parse_plddt

logger = logging.getLogger("dryrun.live.structure")

_DISORDER_PLDDT = 50.0
_MISFOLD_MEAN_PLDDT = 70.0


def _low_confidence_regions(plddt: list[float]) -> list[tuple[int, int]]:
    regions: list[tuple[int, int]] = []
    start: int | None = None
    for i, v in enumerate(plddt):
        if v < _DISORDER_PLDDT and start is None:
            start = i + 1
        elif v >= _DISORDER_PLDDT and start is not None:
            regions.append((start, i))
            start = None
    if start is not None:
        regions.append((start, len(plddt)))
    return regions


class LiveStructureProvider(StructureProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("NVIDIA_API_KEY")
        if not self._api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        self._url = os.getenv(
            "ALPHAFOLD2_URL",
            "https://health.api.nvidia.com/v1/biology/deepmind/alphafold2/predict-structure-from-sequence",
        )
        self._mock = MockStructureProvider()

    def _predict_pdb(self, sequence: str) -> str:
        """ISOLATED external request + unwrap. Returns the PDB text.

        Verify the request/response shape against the current NVIDIA NIM AlphaFold2
        reference; only this function should need changing if the schema moves.
        """
        resp = requests.post(
            self._url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"sequence": sequence, "databases": ["uniref90", "mgnify", "small_bfd"]},
            timeout=600,
        )
        resp.raise_for_status()
        body = resp.json()
        # NIM responses have wrapped the PDB as a string or a single-element list.
        if isinstance(body, list):
            return body[0] if body else ""
        if isinstance(body, dict):
            for key in ("pdb", "structure", "pdbs", "output"):
                if key in body:
                    val = body[key]
                    return val[0] if isinstance(val, list) else val
        if isinstance(body, str):
            return body
        raise ValueError("could not locate PDB in AlphaFold2 response")

    def predict(self, design_id: str, sequence: str) -> StructureResult:
        try:
            pdb = self._predict_pdb(sequence)
            plddt = parse_plddt(pdb)
            if not plddt:
                raise ValueError("no per-residue pLDDT parsed from PDB")
            mean_plddt = sum(plddt) / len(plddt)
            return StructureResult(
                design_id=design_id,
                pdb=pdb,
                plddt=[round(v, 2) for v in plddt],
                mean_plddt=mean_plddt,
                min_plddt=min(plddt),
                low_confidence_regions=_low_confidence_regions(plddt),
                misfold_flag=mean_plddt < _MISFOLD_MEAN_PLDDT,
                method="alphafold2-nim",
                source="nvidia-nim:alphafold2",
            )
        except Exception as exc:  # noqa: BLE001 — graceful fallback
            logger.warning("AlphaFold2 NIM failed for %s (%s); using mock", design_id, exc)
            return self._mock.predict(design_id, sequence)
