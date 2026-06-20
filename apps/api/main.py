"""FastAPI gateway the frontend talks to.

Thin: it resolves request inputs and drives the in-process cascade (Phase 2),
returning the typed Report payload. In Phase 4 it can instead bridge to the live
uAgents, but the in-process path is always available as a reliable fallback so the
demo never depends on all agents being up.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dryrun_agents.shared.cascade import run_cascade
from dryrun_agents.shared.inputs import resolve_inputs
from dryrun_core.models import Report
from dryrun_providers import get_mode

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": get_mode()}


@app.get("/api/demo", response_model=Report)
def demo() -> Report:
    """Run the bundled demo end to end and return the full report."""
    seed, goal, budget, count = resolve_inputs()
    return run_cascade(seed, goal, budget, count)


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
    return run_cascade(seed, goal, budget, count)
