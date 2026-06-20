"""Budget-constrained, diversity-aware portfolio optimizer. Phase 1 implements this.

The intellectual heart of DryRun. Not "rank by score, take top N" — that picks
near-identical designs that fail together. Instead: submodular coverage objective
+ cost-aware greedy with a provable approximation guarantee.
"""

from __future__ import annotations
