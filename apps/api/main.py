"""FastAPI gateway the frontend talks to.

Thin: it resolves request inputs and drives the in-process cascade (Phase 2),
returning the typed Report payload. In Phase 4 it can instead bridge to the live
uAgents, but the in-process path is always available as a reliable fallback so the
demo never depends on all agents being up.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dryrun_agents.shared.cascade import run_cascade
from dryrun_agents.shared.inputs import resolve_inputs
from dryrun_core.models import Report
from dryrun_providers import get_mode, is_strict

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="DryRun API", version="0.1.0")

# The frontend runs on a different origin (Next.js dev server). Permissive CORS is
# fine for a local demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    natural: Optional[str] = None
    seed: Optional[str] = None
    goal: Optional[str] = None
    budget: Optional[float] = None
    candidates: Optional[int] = None


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def root() -> str:
    mode = get_mode()
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>DryRun API</title></head>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;line-height:1.5">
  <h1>DryRun API</h1>
  <p>Backend is running (<code>mode={mode}</code>). This port serves JSON only — not the report UI.</p>
  <p><strong>Open the app:</strong> <a href="http://localhost:3000">http://localhost:3000</a>
     (run <code>make web</code> in a second terminal if it is not up yet).</p>
  <ul>
    <li><a href="/docs">/docs</a> — interactive API docs</li>
    <li><a href="/health">/health</a> — liveness check</li>
    <li><a href="/api/demo">/api/demo</a> — full demo report (JSON)</li>
  </ul>
</body>
</html>"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": get_mode(), "strict": is_strict()}


def _run(seed: str, goal: str, budget: float, count: int) -> Report:
    """Run the cascade, converting a hard failure into a clean 502.

    In DRYRUN_STRICT mode a live provider failure raises by design (no mock
    substitution); surface that as a clear error instead of an opaque 500.
    """
    try:
        return run_cascade(seed, goal, budget, count)
    except Exception as exc:  # noqa: BLE001 — report cleanly to the client
        logging.exception("cascade failed")
        raise HTTPException(
            status_code=502,
            detail=f"Cascade failed ({exc}). In strict mode this means a live "
            f"provider was unavailable; check your keys / DRYRUN_MODE.",
        ) from exc


@app.get("/api/demo", response_model=Report)
def demo() -> Report:
    """Run the bundled demo end to end and return the full report."""
    seed, goal, budget, count = resolve_inputs()
    return _run(seed, goal, budget, count)


@app.post("/api/analyze", response_model=Report)
def analyze(req: AnalyzeRequest) -> Report:
    """Resolve a (natural-language + explicit) request and run the cascade."""
    seed, goal, budget, count = resolve_inputs(
        natural=req.natural,
        seed=req.seed,
        goal=req.goal,
        budget=req.budget,
        candidates=req.candidates,
    )
    return _run(seed, goal, budget, count)
