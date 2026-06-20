"""Sequence -> vector embedding and the dissimilarity metric for diversity.

Phase 1 implements this. The optimizer uses these embeddings to measure how
"distinct" two designs are, so that adding a design similar to ones already
chosen yields diminishing marginal return.
"""

from __future__ import annotations
