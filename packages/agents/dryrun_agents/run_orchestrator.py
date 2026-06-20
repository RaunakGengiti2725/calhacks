"""Run the orchestrator agent standalone (with a mailbox).

    uv run --extra agents python -m dryrun_agents.run_orchestrator

Chat with it in plain English ("improve thermal stability of <seq>, $500, 20
variants"); it coordinates the specialists and returns the report, falling back
to the in-process cascade if any specialist is unreachable.
"""

from __future__ import annotations

from dryrun_agents.shared.build_agent import orchestrator_address
from dryrun_agents.shared.orchestrator import build_orchestrator


def main() -> None:
    agent = build_orchestrator(mailbox=True)
    print(f"orchestrator address: {orchestrator_address()}")
    agent.run()


if __name__ == "__main__":
    main()
