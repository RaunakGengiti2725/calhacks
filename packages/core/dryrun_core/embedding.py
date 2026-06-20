"""Sequence -> vector embedding, a similarity metric, and a 2D projection.

The optimizer measures how "distinct" two designs are in this embedding space so
that adding a design similar to ones already chosen yields diminishing return.

Embedding design: a *position-aware physicochemical* encoding. Each residue maps
to a vector of standardized physicochemical properties (hydropathy, charge,
volume, polarity, aromaticity). The sequence is split into N segments and each
segment is the mean property vector over its residues. The result captures both
*what* changed (which properties) and *where* (which region) — so two variants
that mutate different regions land in different parts of the space, while
near-identical variants stay close. This is derived purely from the sequence, so
it works identically for mock point-mutants and live Evo 2 outputs.

Similarity is rectified cosine: max(0, cos). Identical -> 1, orthogonal/
anti-aligned -> 0. This keeps similarity in [0, 1] (required by the submodular
coverage objective) and gives a crisp diversity signal.
"""

from __future__ import annotations

import numpy as np

AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
_AA_SET = set(AMINO_ACIDS)
N_SEGMENTS = 16

# Literature physicochemical scales (raw; standardized at import below).
_KD_HYDROPATHY = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}
_CHARGE = {"D": -1.0, "E": -1.0, "K": 1.0, "R": 1.0, "H": 0.5}
_VOLUME = {
    "A": 88.6, "R": 173.4, "N": 114.1, "D": 111.1, "C": 108.5, "Q": 143.8,
    "E": 138.4, "G": 60.1, "H": 153.2, "I": 166.7, "L": 166.7, "K": 168.6,
    "M": 162.9, "F": 189.9, "P": 112.7, "S": 89.0, "T": 116.1, "W": 227.8,
    "Y": 193.6, "V": 140.0,
}
_POLARITY = {
    "A": 8.1, "R": 10.5, "N": 11.6, "D": 13.0, "C": 5.5, "Q": 10.5, "E": 12.3,
    "G": 9.0, "H": 10.4, "I": 5.2, "L": 4.9, "K": 11.3, "M": 5.7, "F": 5.2,
    "P": 8.0, "S": 9.2, "T": 8.6, "W": 5.4, "Y": 6.2, "V": 5.9,
}
_AROMATIC = {"F": 1.0, "W": 1.0, "Y": 1.0, "H": 0.5}

_PROP_TABLES = [_KD_HYDROPATHY, _CHARGE, _VOLUME, _POLARITY, _AROMATIC]


def _build_standardized_table() -> tuple[dict[str, np.ndarray], int]:
    mat = np.array(
        [[tbl.get(aa, 0.0) for tbl in _PROP_TABLES] for aa in AMINO_ACIDS],
        dtype=float,
    )  # 20 x n_props
    mean = mat.mean(axis=0)
    std = mat.std(axis=0)
    std[std == 0] = 1.0
    z = (mat - mean) / std
    return {aa: z[i] for i, aa in enumerate(AMINO_ACIDS)}, z.shape[1]


_AA_VEC, _N_PROPS = _build_standardized_table()
_ZERO_PROP = np.zeros(_N_PROPS)


def embed(sequence: str, n_segments: int = N_SEGMENTS) -> np.ndarray:
    """Embed an amino-acid sequence into a fixed-length vector."""
    seq = sequence.strip().upper()
    dim = n_segments * _N_PROPS
    if not seq:
        return np.zeros(dim)
    residue_vecs = np.array([_AA_VEC.get(aa, _ZERO_PROP) for aa in seq])  # L x P
    length = len(seq)
    seg_sum = np.zeros((n_segments, _N_PROPS))
    seg_count = np.zeros(n_segments)
    seg_index = (np.arange(length) * n_segments) // length  # each residue -> segment
    for i, s in enumerate(seg_index):
        seg_sum[s] += residue_vecs[i]
        seg_count[s] += 1
    seg_count[seg_count == 0] = 1.0
    seg_mean = seg_sum / seg_count[:, None]
    return seg_mean.flatten()


def embed_many(sequences: list[str], n_segments: int = N_SEGMENTS) -> np.ndarray:
    if not sequences:
        return np.zeros((0, n_segments * _N_PROPS))
    return np.array([embed(s, n_segments) for s in sequences])


def similarity(u: np.ndarray, v: np.ndarray) -> float:
    """Rectified cosine similarity in [0, 1]; 1 == identical direction."""
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu == 0.0 or nv == 0.0:
        return 0.0
    cos = float(np.dot(u, v) / (nu * nv))
    return max(0.0, min(1.0, cos))


def dissimilarity(u: np.ndarray, v: np.ndarray) -> float:
    """1 - similarity, in [0, 1]; 0 == identical direction."""
    return 1.0 - similarity(u, v)


def similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Pairwise rectified-cosine similarity matrix (n x n), diagonal == 1."""
    emb = np.asarray(embeddings, dtype=float)
    if emb.ndim != 2 or emb.shape[0] == 0:
        return np.zeros((0, 0))
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    unit = emb / norms
    cos = unit @ unit.T
    sim = np.clip(cos, 0.0, 1.0)
    np.fill_diagonal(sim, 1.0)
    return sim


def project_2d(embeddings: np.ndarray) -> list[tuple[float, float]]:
    """Project embeddings to 2D via PCA (numpy SVD). Deterministic sign."""
    emb = np.asarray(embeddings, dtype=float)
    if emb.ndim != 2 or emb.shape[0] == 0:
        return []
    n = emb.shape[0]
    if n == 1:
        return [(0.0, 0.0)]
    centered = emb - emb.mean(axis=0, keepdims=True)
    try:
        u, s, _vt = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError:
        return [(0.0, 0.0)] * n
    comps = u[:, : min(2, u.shape[1])] * s[: min(2, len(s))]
    if comps.shape[1] == 1:
        comps = np.column_stack([comps[:, 0], np.zeros(n)])
    # Deterministic sign: make the largest-magnitude entry on each axis positive.
    for axis in range(2):
        col = comps[:, axis]
        j = int(np.argmax(np.abs(col)))
        if col[j] < 0:
            comps[:, axis] = -col
    return [(float(x), float(y)) for x, y in comps]


__all__ = [
    "AMINO_ACIDS",
    "N_SEGMENTS",
    "embed",
    "embed_many",
    "similarity",
    "dissimilarity",
    "similarity_matrix",
    "project_2d",
]
