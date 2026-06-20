"""Per-run provider provenance — the honest answer to "is this data real?".

Every live provider records, for its stage, whether the real external API actually
produced the result ("live") or the call failed and the mock stood in ("fallback").
The cascade reads this snapshot and stamps it onto the report, so the UI can show,
per stage, exactly what ran — a silent mock fallback can never be presented as a
real API result.

Process-local and isolated per cascade run via a ContextVar: `begin()` installs a
fresh dict at the start of `run_cascade`, and because the whole cascade executes
synchronously within that call's context, every `mark()` from inside it lands in
the same dict. FastAPI runs sync endpoints in a threadpool that copies the context
per request, so concurrent analyses do not bleed into each other.
"""

from __future__ import annotations

from contextvars import ContextVar

# Status values, narrowed for the UI:
#   "live"     — the real external API returned this stage's result
#   "fallback" — live was selected but the call failed; mock data was substituted
#   "mock"     — running in mock mode by design (no live attempt)
#   "local"    — a real in-process algorithm, not an external API (e.g. cost model)
LIVE = "live"
FALLBACK = "fallback"
MOCK = "mock"
LOCAL = "local"

_CURRENT: ContextVar[dict | None] = ContextVar("dryrun_provenance", default=None)


def begin() -> None:
    """Start a fresh provenance record for one cascade run."""
    _CURRENT.set({})


def mark(stage: str, status: str, detail: str = "") -> None:
    """Record the outcome for a stage (no-op if no run is active)."""
    record = _CURRENT.get()
    if record is None:
        return
    record[stage] = {"status": status, "detail": detail}


def snapshot() -> dict[str, dict]:
    """Return a copy of the current run's provenance (stage -> {status, detail})."""
    return dict(_CURRENT.get() or {})


__all__ = ["LIVE", "FALLBACK", "MOCK", "LOCAL", "begin", "mark", "snapshot"]
