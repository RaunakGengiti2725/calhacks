"""Tests for the sequence embedding, similarity metric, and 2D projection."""

from __future__ import annotations

import numpy as np

from dryrun_core.embedding import (
    dissimilarity,
    embed,
    embed_many,
    project_2d,
    similarity,
    similarity_matrix,
)

SEQ = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR"


def test_identical_sequences_have_zero_dissimilarity() -> None:
    u = embed(SEQ)
    v = embed(SEQ)
    assert dissimilarity(u, v) == 0.0
    assert similarity(u, v) == 1.0


def test_embedding_is_deterministic() -> None:
    assert np.array_equal(embed(SEQ), embed(SEQ))


def test_point_mutation_changes_embedding_slightly() -> None:
    mutant = SEQ[:9] + "P" + SEQ[10:]  # one residue changed
    d = dissimilarity(embed(SEQ), embed(mutant))
    assert 0.0 < d < 0.2  # close, but not identical


def test_mutations_in_different_regions_are_distinguishable() -> None:
    early = "P" + SEQ[1:]
    late = SEQ[:-1] + "P"
    # Two mutants of the same seed that change different regions are not identical.
    assert dissimilarity(embed(early), embed(late)) > 0.0


def test_similarity_matrix_diagonal_is_one() -> None:
    emb = embed_many([SEQ, "P" + SEQ[1:], SEQ[:-1] + "P"])
    sim = similarity_matrix(emb)
    assert sim.shape == (3, 3)
    assert np.allclose(np.diag(sim), 1.0)
    assert (sim >= 0.0).all() and (sim <= 1.0).all()


def test_project_2d_shape_and_determinism() -> None:
    emb = embed_many([SEQ, "P" + SEQ[1:], SEQ[:-1] + "P", "A" + SEQ[1:]])
    a = project_2d(emb)
    b = project_2d(emb)
    assert len(a) == 4
    assert all(len(pt) == 2 for pt in a)
    assert a == b  # deterministic sign


def test_empty_and_single_inputs() -> None:
    assert project_2d(embed_many([])) == []
    assert project_2d(embed_many([SEQ])) == [(0.0, 0.0)]
