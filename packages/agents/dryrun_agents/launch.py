"""Run every DryRun agent together in one process (a uAgents Bureau).

    uv run --extra agents python -m dryrun_agents.launch

The Bureau routes Chat-Protocol messages between the agents locally, so the
orchestrator can drive the specialists with no Agentverse/mailbox/network. For
the Agentverse-registered deployment, run agents individually with mailbox=True
(see run_specialist / run_orchestrator) — Phase 5.
"""

from __future__ import annotations

import os
import socket

from uagents import Bureau

from dryrun_agents.shared.agent_config import ORCHESTRATOR, SPECIALISTS
from dryrun_agents.shared.build_agent import (
    address_of,
    build_all_specialists,
    specialist_addresses,
)
from dryrun_agents.shared.orchestrator import build_orchestrator


def bureau_port() -> int:
    return int(os.environ.get("DRYRUN_BUREAU_PORT", "8200"))


def _ensure_port_free(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError as exc:
            raise SystemExit(
                f"Port {port} is already in use (DRYRUN_BUREAU_PORT). "
                f"Stop the other process or run `make stop`, then retry."
            ) from exc


def build_bureau(*, mailbox: bool = False) -> Bureau:
    specialists = build_all_specialists(mailbox=mailbox)
    orchestrator = build_orchestrator(specialist_addresses(), mailbox=mailbox)
    bureau = Bureau(port=bureau_port())
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
    port = bureau_port()
    _ensure_port_free(port)
    print_addresses()
    print(f"\nStarting DryRun Bureau on :{port} — chat with the orchestrator above.\n")
    build_bureau().run()


if __name__ == "__main__":
    main()
