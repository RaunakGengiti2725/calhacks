"""Build the specialist uAgents from the registry.

Each specialist = one stage handler + the Agentverse Chat Protocol. Imports
`uagents` — only loaded inside agent processes / the Bureau.
"""

from __future__ import annotations

import json

from uagents import Agent, Context, Protocol
from uagents.crypto import Identity
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    chat_protocol_spec,
)

from dryrun_agents.shared import handlers as H
from dryrun_agents.shared.agent_config import ORCHESTRATOR, SPECIALISTS
from dryrun_agents.shared.protocol import acknowledge, chat_text, extract_text


def address_of(seed: str) -> str:
    """Deterministic agent address from a fixed seed (no Agent construction)."""
    return Identity.from_seed(seed, 0).address


def specialist_addresses() -> dict[str, str]:
    return {key: address_of(cfg["seed"]) for key, cfg in SPECIALISTS.items()}


def orchestrator_address() -> str:
    return address_of(ORCHESTRATOR["seed"])


def build_specialist(key: str, *, mailbox: bool = False) -> Agent:
    """Construct one specialist agent with its chat-protocol handler."""
    cfg = SPECIALISTS[key]
    handler_fn = getattr(H, cfg["handler"])

    agent = Agent(
        name=f"dryrun-{key.replace('_', '-')}",
        seed=cfg["seed"],
        port=cfg["port"],
        endpoint=[f"http://127.0.0.1:{cfg['port']}/submit"],
        mailbox=mailbox,
        publish_agent_details=True,
        description=cfg["description"],
    )

    proto = Protocol(spec=chat_protocol_spec)

    @proto.on_message(ChatMessage)
    async def _on_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
        await ctx.send(sender, acknowledge(msg))
        text = extract_text(msg)
        try:
            reply = handler_fn(text)
        except Exception as exc:  # noqa: BLE001 — never crash the agent on bad input
            ctx.logger.warning("handler error: %s", exc)
            reply = json.dumps({"error": str(exc)})
        await ctx.send(sender, chat_text(reply, end_session=True))

    @proto.on_message(ChatAcknowledgement)
    async def _on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
        pass

    agent.include(proto, publish_manifest=True)
    return agent


def build_all_specialists(*, mailbox: bool = False) -> dict[str, Agent]:
    return {key: build_specialist(key, mailbox=mailbox) for key in SPECIALISTS}
