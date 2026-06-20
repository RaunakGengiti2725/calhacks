"""Mock sequence-fitness (viability) provider.

Deterministic pseudo-likelihood standing in for Evo 2 sequence scoring. The raw
score is the mean log-frequency of residues under a natural amino-acid background
(so sequences using common, well-tolerated residues score higher) minus small
penalties for structurally implausible local features (proline clusters, charged
runs, homopolymer runs). This is the kind of "biological plausibility" signal a
sequence-likelihood model provides, computed purely from sequence features.
"""

from __future__ import annotations

import math

from dryrun_providers.base import ViabilityProvider

# Natural amino-acid background frequencies (UniProt-scale, %), normalized below.
_AA_FREQ_PCT = {
    "A": 8.25, "R": 5.53, "N": 4.06, "D": 5.45, "C": 1.37, "Q": 3.93, "E": 6.75,
    "G": 7.07, "H": 2.27, "I": 5.96, "L": 9.66, "K": 5.84, "M": 2.42, "F": 3.86,
    "P": 4.70, "S": 6.56, "T": 5.34, "W": 1.08, "Y": 2.92, "V": 6.87,
}
_TOTAL = sum(_AA_FREQ_PCT.values())
_LOG_FREQ = {aa: math.log(pct / _TOTAL) for aa, pct in _AA_FREQ_PCT.items()}
_MIN_LOG = min(_LOG_FREQ.values())

_CHARGED = set("DEKR")


def _local_penalties(seq: str) -> float:
    """Penalize implausible local patterns: PP, long homopolymers, charge runs."""
    penalty = 0.0
    run = 1
    charge_run = 1
    for i in range(1, len(seq)):
        # proline pairs are structurally disruptive
        if seq[i] == "P" and seq[i - 1] == "P":
            penalty += 0.35
        # homopolymer runs
        if seq[i] == seq[i - 1]:
            run += 1
            if run >= 3:
                penalty += 0.15
        else:
            run = 1
        # consecutive same-region charged residues
        if seq[i] in _CHARGED and seq[i - 1] in _CHARGED:
            charge_run += 1
            if charge_run >= 3:
                penalty += 0.10
        else:
            charge_run = 1
    return penalty


class MockViabilityProvider(ViabilityProvider):
    def score(self, sequences: list[str]) -> list[float]:
        return [self._raw(s) for s in sequences]

    def _raw(self, sequence: str) -> float:
        seq = sequence.strip().upper()
        if not seq:
            return _MIN_LOG
        mean_log = sum(_LOG_FREQ.get(aa, _MIN_LOG - 1.0) for aa in seq) / len(seq)
        return mean_log - _local_penalties(seq)
