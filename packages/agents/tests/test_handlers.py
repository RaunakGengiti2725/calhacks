"""Tests for the specialist JSON contracts (uagents-free — runs on light install)."""

from __future__ import annotations

import json
import os

os.environ.setdefault("DRYRUN_MODE", "mock")

from dryrun_agents.shared import handlers as H  # noqa: E402
from dryrun_agents.shared.demo import DEMO_SEED  # noqa: E402

GOAL = "improve thermal stability"


def test_generation_handler_returns_designs() -> None:
    out = json.loads(H.generation_handler(json.dumps({"seed": DEMO_SEED, "goal": GOAL, "n": 6})))
    assert len(out["designs"]) == 6
    assert all(d["sequence"] for d in out["designs"])


def test_fitness_handler_scores_sequences() -> None:
    out = json.loads(H.fitness_handler(json.dumps({"sequences": {"a": DEMO_SEED}})))
    assert "a" in out["viability"]
    assert 0.0 <= out["viability"]["a"]["score"] <= 1.0


def test_fold_handler_returns_structure() -> None:
    out = json.loads(H.fold_handler(json.dumps({"sequences": {"a": DEMO_SEED}})))
    s = out["structures"]["a"]
    assert len(s["plddt"]) == len(DEMO_SEED)
    assert s["pdb"]


def test_cost_handler_returns_cost() -> None:
    out = json.loads(H.cost_handler(json.dumps({"sequences": {"a": DEMO_SEED}})))
    assert out["costs"]["a"]["total_cost"] > 0


def test_handlers_answer_natural_language_standalone() -> None:
    # A stranger messaging the agent in English still gets a useful reply.
    out = json.loads(H.fitness_handler("how plausible is this protein?"))
    assert "message" in out and out["agent"] == "sequence-fitness"


def test_optimizer_handler_via_full_pipeline() -> None:
    from dryrun_agents.shared import stages

    designs = stages.generate(DEMO_SEED, GOAL, 16)
    viability = stages.score_viability(designs)
    survivors = stages.viability_survivors(designs, viability)
    structures = stages.fold(survivors)
    costs = stages.estimate_costs(designs)
    scored = stages.build_scored(designs, viability, structures, costs)
    pool = [sd for sd in scored if sd.passed_fold]

    out = json.loads(
        H.optimizer_handler(json.dumps({"pool": [sd.model_dump() for sd in pool], "budget": 500.0}))
    )
    comp = out["comparison"]
    assert comp["optimized"]["expected_distinct_successes"] > comp["naive"]["expected_distinct_successes"]
