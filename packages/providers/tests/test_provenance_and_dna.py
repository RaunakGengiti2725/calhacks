"""Tests for the new live-path plumbing: .env config, provenance, strict mode,
protein<->DNA conversion, and the Evo 2 NPZ likelihood math. No network/keys."""

from __future__ import annotations

import base64
import io

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# protein <-> DNA round-trip (Evo 2 bridge)
# --------------------------------------------------------------------------- #
def test_protein_dna_roundtrip_is_identity_for_standard_residues() -> None:
    from dryrun_providers.live._dna import dna_to_protein, protein_to_dna

    protein = "MKAILVTTCPSIVARSNFNVCRLPGT"
    dna = protein_to_dna(protein)
    assert len(dna) == len(protein) * 3
    assert set(dna) <= set("ACGT")
    assert dna_to_protein(dna) == protein


def test_dna_to_protein_stops_at_stop_codon() -> None:
    from dryrun_providers.live._dna import dna_to_protein

    # ATG=M, AAA=K, TAA=stop, then GGG should be ignored.
    assert dna_to_protein("ATGAAATAAGGG") == "MK"


# --------------------------------------------------------------------------- #
# Evo 2 forward NPZ -> log-likelihood parsing (isolated math)
# --------------------------------------------------------------------------- #
def test_evo2_likelihood_parses_npz_and_scores() -> None:
    from dryrun_providers.live.viability import _logits_from_npz, _mean_log_likelihood

    dna = "ACGTACGT"
    # Build [seq_len, 1, 512] logits that strongly favor each actual next base.
    logits = np.full((len(dna), 1, 512), -10.0, dtype=np.float32)
    for i in range(len(dna) - 1):
        logits[i, 0, ord(dna[i + 1])] = 10.0
    buf = io.BytesIO()
    np.savez(buf, output_layer=logits)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    parsed = _logits_from_npz(b64)
    assert parsed.shape[-1] == 512
    ll = _mean_log_likelihood(dna, parsed)
    assert ll > -0.5  # confident correct predictions -> near-zero log-likelihood


# --------------------------------------------------------------------------- #
# provenance recorder
# --------------------------------------------------------------------------- #
def test_provenance_records_per_run() -> None:
    from dryrun_providers import provenance

    provenance.begin()
    provenance.mark("viability", provenance.LIVE, "ok")
    snap = provenance.snapshot()
    assert snap["viability"]["status"] == "live"
    assert snap["viability"]["detail"] == "ok"


def test_provenance_mark_without_begin_is_noop() -> None:
    from dryrun_providers import provenance

    # A fresh ContextVar with no begin() must not raise.
    provenance.mark("structure", provenance.LIVE)  # no error


# --------------------------------------------------------------------------- #
# strict mode: a missing key RAISES at the factory instead of mock fallback
# --------------------------------------------------------------------------- #
def test_strict_mode_raises_instead_of_mock_fallback(monkeypatch) -> None:
    monkeypatch.setenv("DRYRUN_MODE", "live")
    monkeypatch.setenv("DRYRUN_STRICT", "1")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    from dryrun_providers import factory

    with pytest.raises(RuntimeError, match="DRYRUN_STRICT"):
        factory.get_generation_provider()


def test_non_strict_live_without_keys_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("DRYRUN_MODE", "live")
    monkeypatch.delenv("DRYRUN_STRICT", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    from dryrun_providers import factory

    assert type(factory.get_generation_provider()).__name__ == "MockGenerationProvider"
