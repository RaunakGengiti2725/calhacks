"""Protein <-> DNA conversion for the Evo 2 live path.

Evo 2 (`arc/evo2-40b`) is a *genomic* foundation model: its tokens are DNA bases
(A/C/G/T), not amino acids. DryRun's pipeline is protein-centric, so the live
Evo 2 providers must bridge the two:

  * generation  — back-translate the seed protein to DNA, let Evo 2 extend/sample
                  DNA, then translate the DNA back to a protein variant.
  * viability   — back-translate each protein to DNA and score the DNA likelihood
                  with Evo 2's forward pass.

Back-translation is inherently many-to-one (most amino acids have several codons),
so we pick one fixed, highly-expressed codon per residue (an E. coli-biased table).
This is a deterministic, standard choice — good enough to give Evo 2 a biologically
real DNA context — but it is NOT a unique inverse, which is one reason the live
Evo 2 path is documented as "doc-matched, pending live verification".
"""

from __future__ import annotations

# Standard genetic code: codon -> amino acid ("*" = stop).
CODON_TABLE: dict[str, str] = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# One preferred (highly-expressed, E. coli-biased) codon per amino acid, used for
# the deterministic protein -> DNA back-translation.
PREFERRED_CODON: dict[str, str] = {
    "A": "GCG", "R": "CGT", "N": "AAC", "D": "GAT", "C": "TGC",
    "Q": "CAG", "E": "GAA", "G": "GGC", "H": "CAT", "I": "ATT",
    "L": "CTG", "K": "AAA", "M": "ATG", "F": "TTT", "P": "CCG",
    "S": "AGC", "T": "ACC", "W": "TGG", "Y": "TAT", "V": "GTG",
}

_AA = set("ACDEFGHIKLMNPQRSTVWY")


def protein_to_dna(protein: str) -> str:
    """Back-translate a protein to a DNA coding sequence (deterministic codons).

    Unknown residues are skipped. No start/stop codons are added — Evo 2 scores raw
    nucleotide context, and the caller controls how much to generate.
    """
    return "".join(PREFERRED_CODON[a] for a in protein.strip().upper() if a in _AA)


def dna_to_protein(dna: str) -> str:
    """Translate a DNA string in frame 0, stopping at the first stop codon.

    Bases outside A/C/G/T and trailing partial codons are dropped. Returns the
    amino-acid string (may be empty if nothing valid translated).
    """
    clean = "".join(c for c in dna.strip().upper() if c in "ACGT")
    out: list[str] = []
    for i in range(0, len(clean) - 2, 3):
        aa = CODON_TABLE.get(clean[i : i + 3])
        if aa is None:
            continue
        if aa == "*":
            break
        out.append(aa)
    return "".join(out)


__all__ = ["CODON_TABLE", "PREFERRED_CODON", "protein_to_dna", "dna_to_protein"]
