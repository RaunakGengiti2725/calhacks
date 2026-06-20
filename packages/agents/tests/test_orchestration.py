"""Tests for the multi-agent orchestration (gated on the uagents extra being installed)."""

from __future__ import annotations

import asyncio
import logging
import os

import pytest

os.environ.setdefault("DRYRUN_MODE", "mock")

pytest.importorskip("uagents", reason="uagents extra not installed (light demo install)")

from dryrun_agents.shared import handlers as H  # noqa: E402
from dryrun_agents.shared.agent_config import SPECIALISTS  # noqa: E402
from dryrun_agents.shared.demo import DEMO_BUDGET, DEMO_GOAL, DEMO_SEED  # noqa: E402
from dryrun_agents.shared.orchestrator import orchestrate  # noqa: E402
from dryrun_agents.shared.protocol import chat_text, extract_text  # noqa: E402


class _FakeContext:
    """Routes send_and_receive directly to the in-process handlers, exercising the
    real orchestrate() coordination + real handler contracts without networking."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("test.orchestrator")
        self._handlers = {key: getattr(H, cfg["handler"]) for key, cfg in SPECIALISTS.items()}

    async def send_and_receive(self, dest, message, response_type=None, timeout=30, sync=False):
        text = extract_text(message)
        reply = self._handlers[dest](text)  # dest == specialist key (fake address)
        return chat_text(reply), None


def test_deterministic_addresses_are_stable() -> None:
    from dryrun_agents.shared.build_agent import address_of

    a = address_of(SPECIALISTS["sequence_fitness"]["seed"])
    b = address_of(SPECIALISTS["sequence_fitness"]["seed"])
    assert a == b and a.startswith("agent1")


def test_build_bureau_constructs_all_agents() -> None:
    from dryrun_agents.launch import build_bureau

    bureau = build_bureau()
    assert bureau is not None  # all 6 specialists + orchestrator built without error


def test_orchestrate_drives_specialists_and_returns_report() -> None:
    address_map = {key: key for key in SPECIALISTS}  # fake addresses == keys
    ctx = _FakeContext()
    report = asyncio.run(
        orchestrate(ctx, address_map, DEMO_SEED, DEMO_GOAL, DEMO_BUDGET, 20)
    )
    # the multi-agent path produces the same honest, diversity-winning result
    assert report.funnel.generated == 20
    assert report.funnel.fold_passed <= report.funnel.viability_passed
    assert (
        report.summary.expected_distinct_successes
        > report.summary.naive_expected_distinct_successes
    )
    assert report.summary.expected_distinct_successes <= report.summary.designs_selected + 1e-9


def test_orchestrated_result_matches_in_process_cascade() -> None:
    from dryrun_agents.shared.cascade import run_cascade

    address_map = {key: key for key in SPECIALISTS}
    ctx = _FakeContext()
    via_agents = asyncio.run(orchestrate(ctx, address_map, DEMO_SEED, DEMO_GOAL, DEMO_BUDGET, 20))
    in_process = run_cascade(DEMO_SEED, DEMO_GOAL, DEMO_BUDGET, 20)
    # agent path and fallback path agree on the selection and headline metrics
    assert via_agents.comparison.optimized.selected_ids == in_process.comparison.optimized.selected_ids
    assert (
        round(via_agents.summary.expected_distinct_successes, 3)
        == round(in_process.summary.expected_distinct_successes, 3)
    )
