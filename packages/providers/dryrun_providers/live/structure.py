"""Live fold-risk provider — AlphaFold2 via NVIDIA NIM.

Calls the hosted `predict-structure-from-sequence` endpoint, which returns a PDB
whose B-factor column holds per-residue pLDDT; we parse that with the shared
pdb_utils (the one place that knows the PDB column layout).

The hosted health.api.nvidia.com biology endpoints are NVCF functions: a slow job
(AlphaFold2's MSA takes minutes) returns HTTP 202 with an `nvcf-reqid`, and the
result must be polled at the status URL until 200. `_predict_pdb` handles BOTH the
synchronous 200 and the async 202 -> poll -> 200 cases, so a real call actually
returns a structure instead of silently timing out into mock. The request/unwrap
is isolated here; a changed schema is a one-function fix. Falls back to mock on any
error / missing key (unless DRYRUN_STRICT), recording the path in `provenance`.

Scoping note: full MSA-based AlphaFold2 is slow, so the cascade caps how many
viability survivors are folded (DRYRUN_FOLD_CAP).
"""

from __future__ import annotations

import logging
import os
import time

import requests

from dryrun_core.models import StructureResult
from dryrun_providers import provenance
from dryrun_providers.base import StructureProvider
from dryrun_providers.config import is_strict
from dryrun_providers.mock.structure import MockStructureProvider
from dryrun_providers.pdb_utils import parse_plddt

logger = logging.getLogger("dryrun.live.structure")

_STAGE = "structure"
_DISORDER_PLDDT = 50.0
_MISFOLD_MEAN_PLDDT = 70.0
_DEFAULT_URL = (
    "https://health.api.nvidia.com/v1/biology/deepmind/alphafold2/"
    "predict-structure-from-sequence"
)
_DEFAULT_STATUS_URL = "https://health.api.nvidia.com/v1/status"
_POLL_INTERVAL_S = 10
_MAX_POLLS = 50  # up to ~8 min of polling for a slow MSA job


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


def _unwrap_pdb(body: object) -> str:
    """Pull the PDB text out of whatever shape the response/result uses."""
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


class LiveStructureProvider(StructureProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("NVIDIA_API_KEY")
        if not self._api_key:
            raise RuntimeError("NVIDIA_API_KEY not set")
        self._url = os.getenv("ALPHAFOLD2_URL", _DEFAULT_URL)
        self._status_url = os.getenv("NVCF_STATUS_URL", _DEFAULT_STATUS_URL).rstrip("/")
        self._mock = MockStructureProvider()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _predict_pdb(self, sequence: str) -> str:
        """ISOLATED external request + (async poll) + unwrap. Returns PDB text.

        Handles the NVCF pattern: 202 + `nvcf-reqid` -> poll status URL until 200.
        """
        resp = requests.post(
            self._url,
            headers=self._headers,
            json={
                "sequence": sequence,
                "databases": ["uniref90", "mgnify", "small_bfd"],
            },
            timeout=300,
        )
        # 202 => async job: poll the status endpoint with the returned request id.
        if resp.status_code == 202:
            req_id = resp.headers.get("nvcf-reqid") or resp.headers.get("NVCF-REQID")
            if not req_id:
                raise ValueError("202 from AlphaFold2 but no nvcf-reqid header")
            for _ in range(_MAX_POLLS):
                time.sleep(_POLL_INTERVAL_S)
                poll = requests.get(
                    f"{self._status_url}/{req_id}", headers=self._headers, timeout=60
                )
                if poll.status_code == 202:
                    continue
                poll.raise_for_status()
                return _unwrap_pdb(poll.json())
            raise TimeoutError("AlphaFold2 job did not finish within poll budget")
        resp.raise_for_status()
        return _unwrap_pdb(resp.json())

    def predict(self, design_id: str, sequence: str) -> StructureResult:
        try:
            pdb = self._predict_pdb(sequence)
            plddt = parse_plddt(pdb)
            if not plddt:
                raise ValueError("no per-residue pLDDT parsed from PDB")
            mean_plddt = sum(plddt) / len(plddt)
            provenance.mark(_STAGE, provenance.LIVE, "alphafold2-nim")
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
        except Exception as exc:  # noqa: BLE001 — graceful fallback unless strict
            if is_strict():
                raise
            logger.warning("AlphaFold2 NIM failed for %s (%s); using mock", design_id, exc)
            provenance.mark(_STAGE, provenance.FALLBACK, str(exc))
            return self._mock.predict(design_id, sequence)
