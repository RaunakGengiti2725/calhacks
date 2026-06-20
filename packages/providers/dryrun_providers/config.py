"""Process configuration — load the repo `.env` ONCE, expose mode/strict helpers.

This module is imported by `dryrun_providers/__init__`, so the repo-root `.env` is
read before any `os.getenv` in the providers, cascade, API, or agents. Without it,
keys pasted into `.env` would be silently ignored — `python-dotenv` does not load
itself, and `os.getenv` never reads a file. That silent gap is exactly what makes
"I set DRYRUN_MODE=live and a key but it still returns mock data" happen.

Precedence (highest first): a variable already set in the real environment (e.g.
your shell or `make live`) wins over `.env`; `.env` wins over the in-code default.
That is the standard, least-surprising order — so `.env` is authoritative for a
local run, but an explicit shell export can still override it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_LOADED = False


def load_env() -> None:
    """Load the repo-root `.env` exactly once (idempotent, override=False)."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    # Keep the test suite hermetic: never let a developer's local `.env` change
    # test outcomes. Tests set what they need explicitly (monkeypatch).
    if "pytest" in sys.modules:
        return
    # config.py lives at packages/providers/dryrun_providers/config.py
    # parents: [0]=dryrun_providers [1]=providers [2]=packages [3]=repo root
    repo_root = Path(__file__).resolve().parents[3]
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        # Fall back to the standard upward search from the current directory.
        load_dotenv(override=False)


# Load immediately on import so every downstream os.getenv sees .env values.
load_env()


def is_strict() -> bool:
    """When true, a LIVE provider RAISES on failure instead of silently using mock.

    Default (false): live calls fall back to mock per-call so a demo never hard-
    fails — but the fallback is recorded in provenance and shown in the UI, so it
    never masquerades as real. Set DRYRUN_STRICT=1 to instead surface any live
    failure loudly (no mock substitution) — the way to *guarantee* a run is 100%
    real external data with nothing silently swapped underneath.
    """
    return os.getenv("DRYRUN_STRICT", "").strip().lower() in {"1", "true", "yes", "on"}


__all__ = ["load_env", "is_strict"]
