"""Isolated PDB parsing/rewriting — the one place that knows PDB column layout.

Both the mock structure provider (writes synthetic pLDDT into the B-factor column)
and the live AlphaFold2 provider (reads per-residue pLDDT from the B-factor column)
go through here, so a format quirk is a one-file fix.

PDB fixed-column layout used:
  record name [0:6], resName [17:20], chainID [21], resSeq [22:26],
  tempFactor/B-factor [60:66]  (Real(6.2))
"""

from __future__ import annotations

THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}

_ATOM_RECORDS = ("ATOM  ", "HETATM")


def _is_atom(line: str) -> bool:
    return line.startswith("ATOM") or line.startswith("HETATM")


def residue_keys(pdb_text: str) -> list[tuple[str, str]]:
    """Ordered unique (chainID, resSeq) keys across ATOM records."""
    seen: list[tuple[str, str]] = []
    seen_set: set[tuple[str, str]] = set()
    for line in pdb_text.splitlines():
        if not _is_atom(line) or len(line) < 26:
            continue
        key = (line[21], line[22:26])
        if key not in seen_set:
            seen_set.add(key)
            seen.append(key)
    return seen


def extract_sequence(pdb_text: str) -> str:
    """One-letter sequence in residue order (unknown residues -> 'X')."""
    seq: list[str] = []
    seen_set: set[tuple[str, str]] = set()
    for line in pdb_text.splitlines():
        if not _is_atom(line) or len(line) < 26:
            continue
        key = (line[21], line[22:26])
        if key in seen_set:
            continue
        seen_set.add(key)
        seq.append(THREE_TO_ONE.get(line[17:20].strip(), "X"))
    return "".join(seq)


def parse_plddt(pdb_text: str) -> list[float]:
    """Per-residue confidence = mean B-factor over each residue's atoms, in order.

    This is exactly how pLDDT is read back from an AlphaFold2 PDB (it stores the
    per-residue pLDDT in the B-factor column).
    """
    order: list[tuple[str, str]] = []
    sums: dict[tuple[str, str], float] = {}
    counts: dict[tuple[str, str], int] = {}
    for line in pdb_text.splitlines():
        if not _is_atom(line) or len(line) < 66:
            continue
        key = (line[21], line[22:26])
        try:
            b = float(line[60:66])
        except ValueError:
            continue
        if key not in counts:
            order.append(key)
            sums[key] = 0.0
            counts[key] = 0
        sums[key] += b
        counts[key] += 1
    return [sums[k] / counts[k] for k in order]


def set_plddt(pdb_text: str, plddt: list[float]) -> str:
    """Return a copy of the PDB with each residue's B-factor set to its pLDDT.

    `plddt` is aligned to residue order (see `residue_keys`). Residues beyond the
    list keep their original B-factor.
    """
    keys = residue_keys(pdb_text)
    value_by_key = {k: plddt[i] for i, k in enumerate(keys) if i < len(plddt)}
    out: list[str] = []
    for line in pdb_text.splitlines():
        if _is_atom(line) and len(line) >= 66:
            key = (line[21], line[22:26])
            if key in value_by_key:
                b = max(0.0, min(999.99, value_by_key[key]))
                line = line[:60] + f"{b:6.2f}" + line[66:]
        out.append(line)
    return "\n".join(out) + "\n"


__all__ = [
    "THREE_TO_ONE",
    "residue_keys",
    "extract_sequence",
    "parse_plddt",
    "set_plddt",
]
