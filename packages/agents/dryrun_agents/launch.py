"""Run every DryRun agent together in one process (a uAgents Bureau).

    uv run --extra agents python -m dryrun_agents.launch

The Bureau routes Chat-Protocol messages between the agents locally, so the
orchestrator can drive the specialists with no Agentverse/mailbox/network. For
the Agentverse-registered deployment, run agents individually with mailbox=True
(see run_specialist / run_orchestrator) — Phase 5.
"""

from __future__ import annotations

from uagents import Bureau

from dryrun_agents.shared.agent_config import ORCHESTRATOR, SPECIALISTS
from dryrun_agents.shared.build_agent import (
    address_of,
    build_all_specialists,
    specialist_addresses,
)
from dryrun_agents.shared.orchestrator import build_orchestrator


def build_bureau(*, mailbox: bool = False) -> Bureau:
    specialists = build_all_specialists(mailbox=mailbox)
    orchestrator = build_orchestrator(specialist_addresses(), mailbox=mailbox)
    bureau = Bureau()
    for agent in specialists.values():
        bureau.add(agent)
    bureau.add(orchestrator)
    return bureau


def print_addresses() -> None:
    print("DryRun agent addresses (deterministic from fixed seeds):")
    print(f"  orchestrator        {address_of(ORCHESTRATOR['seed'])}")
    for key in SPECIALISTS:
        print(f"  {key:<20}{address_of(SPECIALISTS[key]['seed'])}")


def main() -> None:
    print_addresses()
    print("\nStarting DryRun Bureau — chat with the orchestrator above.\n")
    build_bureau().run()


if __name__ == "__main__":
    main()
