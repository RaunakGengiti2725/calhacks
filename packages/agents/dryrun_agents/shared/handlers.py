"""Per-specialist request handlers — the JSON contract each agent speaks.

Each handler is a pure `str -> str` function: it parses a JSON request (or a
plain-English message, for standalone discovery use), runs exactly one cascade
stage, and returns a JSON response. These import only core/providers (NO
`uagents`), so the whole agent contract is unit-testable on the light install and
the agent wrappers stay trivial.
"""

from __future__ import annotations

import json
import re

from dryrun_agents.shared import stages
from dryrun_core.models import Design, ScoredDesign
from dryrun_core.optimizer import build_comparison
from dryrun_providers import get_viability_provider

_AA_SEQ = re.compile(r"\b[ACDEFGHIKLMNPQRSTVWY]{12,}\b")


def _maybe_json(text: str) -> dict | None:
    text = text.strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _designs_from(req: dict) -> list[Design]:
    if "designs" in req:
        return [Design.model_validate(d) for d in req["designs"]]
    seqs = req.get("sequences", {})
    return [Design(id=k, sequence=v) for k, v in seqs.items()]


# ---------------------------------------------------------------------------
# Specialist handlers
# ---------------------------------------------------------------------------


def generation_handler(text: str) -> str:
    """Design Generator: propose N variants of a seed toward a goal."""
    req = _maybe_json(text)
    if req is None:
        m = _AA_SEQ.search(text.upper())
        if not m:
            return _describe(
                "design-generator",
                "Propose N variants of a protein toward a goal. Send JSON "
                '{"seed": "<sequence>", "goal": "<text>", "n": <int>} or include a '
                "sequence in your message.",
            )
        req = {"seed": m.group(0), "goal": text, "n": 8}
    designs = stages.generate(req["seed"], req.get("goal", ""), int(req.get("n", 8)))
    return json.dumps({"designs": [d.model_dump() for d in designs]})


def fitness_handler(text: str) -> str:
    """Sequence Fitness: normalized biological-plausibility score per sequence."""
    req = _maybe_json(text)
    if req is None:
        m = _AA_SEQ.search(text.upper())
        if not m:
            return _describe(
                "sequence-fitness",
                "Score how biologically plausible a sequence is. Send JSON "
                '{"sequences": {"id": "<seq>"}} or include a sequence.',
            )
        req = {"sequences": {"q": m.group(0)}}
    designs = _designs_from(req)
    viability = stages.score_viability(designs)
    return json.dumps({"viability": {k: v.model_dump() for k, v in viability.items()}})


def fold_handler(text: str) -> str:
    """Fold Risk: structure + per-residue confidence + misfold flag."""
    req = _maybe_json(text)
    if req is None:
        m = _AA_SEQ.search(text.upper())
        if not m:
            return _describe(
                "fold-risk",
                "Predict whether a protein folds and where it is structurally "
                'fragile. Send JSON {"sequences": {"id": "<seq>"}}.',
            )
        req = {"sequences": {"q": m.group(0)}}
    designs = _designs_from(req)
    structures = stages.fold(designs)
    return json.dumps({"structures": {k: v.model_dump() for k, v in structures.items()}})


def cost_handler(text: str) -> str:
    """Synthesis Cost: estimated synthesis + cloning cost per construct."""
    req = _maybe_json(text)
    if req is None:
        m = _AA_SEQ.search(text.upper())
        if not m:
            return _describe(
                "synthesis-cost",
                "Estimate what a construct costs to manufacture. Send JSON "
                '{"sequences": {"id": "<seq>"}}.',
            )
        req = {"sequences": {"q": m.group(0)}}
    designs = _designs_from(req)
    costs = stages.estimate_costs(designs)
    return json.dumps({"costs": {k: v.model_dump() for k, v in costs.items()}})


def optimizer_handler(text: str) -> str:
    """Portfolio Optimizer: budget-constrained, diversity-aware selection."""
    req = _maybe_json(text)
    if req is None:
        return _describe(
            "portfolio-optimizer",
            "Given scored designs and a budget, choose what to actually buy. Send "
            'JSON {"pool": [ScoredDesign...], "budget": <float>}.',
        )
    pool = [ScoredDesign.model_validate(d) for d in req.get("pool", [])]
    comparison = build_comparison(pool, float(req.get("budget", 0.0)))
    return json.dumps({"comparison": comparison.model_dump()})


def reporting_handler(text: str) -> str:
    """Reporting: assemble the full researcher-facing report payload."""
    from dryrun_core.models import PortfolioComparison

    req = _maybe_json(text)
    if req is None:
        return _describe(
            "reporting",
            "Turn an analysis into a shareable report payload. Send JSON with "
            "seed, goal, budget, candidate_count, designs, scored, comparison.",
        )
    designs = [Design.model_validate(d) for d in req["designs"]]
    scored = [ScoredDesign.model_validate(s) for s in req["scored"]]
    comparison = PortfolioComparison.model_validate(req["comparison"])
    report = stages.assemble_report(
        seed=req["seed"],
        goal=req.get("goal", ""),
        budget=float(req["budget"]),
        candidate_count=int(req["candidate_count"]),
        designs=designs,
        scored=scored,
        comparison=comparison,
    )
    return json.dumps({"report": report.model_dump()})


def _describe(name: str, text: str) -> str:
    return json.dumps({"agent": name, "message": text})
