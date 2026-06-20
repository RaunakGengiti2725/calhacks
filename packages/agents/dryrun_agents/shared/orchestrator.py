"""The orchestrator agent — the one a researcher chats with.

It parses the natural-language request (LLM), then coordinates the cascade by
messaging the specialist agents over the Chat Protocol (`send_and_receive`):
generate → fitness (all) → fold (survivors only) → cost → optimize. The scoring
glue and final report assembly run locally to avoid round-tripping large
structure payloads. If any specialist is unreachable, it logs a warning and
falls back to the in-process cascade, so the demo never hard-fails.
"""

from __future__ import annotations

import json

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    chat_protocol_spec,
)

from dryrun_agents.shared import stages
from dryrun_agents.shared.agent_config import ORCHESTRATOR
from dryrun_agents.shared.build_agent import specialist_addresses
from dryrun_agents.shared.cascade import run_cascade
from dryrun_agents.shared.inputs import resolve_inputs
from dryrun_agents.shared.protocol import acknowledge, chat_text, extract_text
from dryrun_core.models import (
    CostEstimate,
    Design,
    PortfolioComparison,
    Report,
    StructureResult,
    ViabilityScore,
)


async def _ask(ctx: Context, address: str, payload: dict, timeout: int = 30) -> dict:
    """Send a JSON request to a specialist and return its parsed JSON reply."""
    reply, status = await ctx.send_and_receive(
        address, chat_text(json.dumps(payload)), response_type=ChatMessage, timeout=timeout
    )
    if reply is None or not isinstance(reply, ChatMessage):
        raise RuntimeError(f"no reply from {address}: {status}")
    data = json.loads(extract_text(reply))
    if "error" in data:
        raise RuntimeError(f"specialist error: {data['error']}")
    return data


async def orchestrate(
    ctx: Context,
    address_map: dict[str, str],
    seed: str,
    goal: str,
    budget: float,
    n: int,
    *,
    fold_cap: int = stages.DEFAULT_FOLD_CAP,
) -> Report:
    """Drive the full cascade across the specialist agents and assemble the report."""
    # 1. Design Generator
    r = await _ask(ctx, address_map["design_generator"], {"seed": seed, "goal": goal, "n": n})
    designs = [Design.model_validate(d) for d in r["designs"]]

    # 2. Sequence Fitness (whole pool) -> filter
    r = await _ask(ctx, address_map["sequence_fitness"], {"designs": [d.model_dump() for d in designs]})
    viability = {k: ViabilityScore.model_validate(v) for k, v in r["viability"].items()}
    survivors = stages.viability_survivors(designs, viability)

    # 3. Fold Risk (survivors only)
    r = await _ask(
        ctx, address_map["fold_risk"], {"designs": [d.model_dump() for d in survivors[:fold_cap]]}
    )
    structures = {k: StructureResult.model_validate(v) for k, v in r["structures"].items()}

    # 4. Synthesis Cost (whole pool)
    r = await _ask(ctx, address_map["synthesis_cost"], {"designs": [d.model_dump() for d in designs]})
    costs = {k: CostEstimate.model_validate(v) for k, v in r["costs"].items()}

    # 5. Scoring glue (local): embeddings + success probability
    scored = stages.build_scored(designs, viability, structures, costs)
    pool = [sd for sd in scored if sd.passed_fold]

    # 6. Portfolio Optimizer
    r = await _ask(
        ctx,
        address_map["portfolio_optimizer"],
        {"pool": [sd.model_dump() for sd in pool], "budget": budget},
    )
    comparison = PortfolioComparison.model_validate(r["comparison"])

    # 7. Report assembly (local — avoids a multi-MB structure round-trip)
    return stages.assemble_report(
        seed=seed,
        goal=goal,
        budget=budget,
        candidate_count=n,
        designs=designs,
        scored=scored,
        comparison=comparison,
    )


def build_orchestrator(address_map: dict[str, str] | None = None, *, mailbox: bool = False) -> Agent:
    """Construct the orchestrator agent. `address_map` defaults to the deterministic
    specialist addresses (config fallback); Phase 5 swaps in Agentverse discovery."""
    addresses = address_map or specialist_addresses()

    agent = Agent(
        name="dryrun-orchestrator",
        seed=ORCHESTRATOR["seed"],
        port=ORCHESTRATOR["port"],
        endpoint=[f"http://127.0.0.1:{ORCHESTRATOR['port']}/submit"],
        mailbox=mailbox,
        publish_agent_details=True,
        description=ORCHESTRATOR["description"],
    )

    proto = Protocol(spec=chat_protocol_spec)

    @proto.on_message(ChatMessage)
    async def _on_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
        await ctx.send(sender, acknowledge(msg))
        text = extract_text(msg)
        seed, goal, budget, n = resolve_inputs(natural=text or None)
        try:
            report = await orchestrate(ctx, addresses, seed, goal, budget, n)
            via = "multi-agent"
        except Exception as exc:  # noqa: BLE001 — reliability: fall back, never crash
            ctx.logger.warning("multi-agent path failed (%s); using in-process cascade", exc)
            report = run_cascade(seed, goal, budget, n)
            via = "in-process fallback"
        ctx.logger.info("DryRun report ready via %s", via)
        await ctx.send(
            sender,
            chat_text(
                json.dumps({"summary": report.plain_summary, "report": report.model_dump(), "via": via}),
                end_session=True,
            ),
        )

    @proto.on_message(ChatAcknowledgement)
    async def _on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        pass

    agent.include(proto, publish_manifest=True)
    return agent
