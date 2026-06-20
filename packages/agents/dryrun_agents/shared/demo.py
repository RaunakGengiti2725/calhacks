"""Bundled demo inputs so `make demo` / `make web` run with zero configuration.

The seed is crambin (PDB 1CRN), the small public-domain protein whose real
structure is bundled for the 3D viewer.
"""

from __future__ import annotations

DEMO_SEED = "TTCCPSIVARSNFNVCRLPGTPEAICATYTGCIIIPGATCPGDYAN"  # crambin (PDB 1CRN)
DEMO_GOAL = "improve thermal stability"
DEMO_BUDGET = 500.0
DEMO_CANDIDATES = 20
