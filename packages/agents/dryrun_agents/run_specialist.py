"""Run a single specialist agent standalone (its own server, optionally a mailbox).

    uv run --extra agents python -m dryrun_agents.run_specialist sequence_fitness

Each specialist is independently messageable and useful on its own (e.g. "score
how plausible this sequence is") — exactly the Agentverse standalone-value test.
"""

from __future__ import annotations

import sys

from dryrun_agents.shared.agent_config import SPECIALISTS
from dryrun_agents.shared.build_agent import address_of, build_specialist


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in SPECIALISTS:
        print(f"usage: run_specialist <{'|'.join(SPECIALISTS)}>")
        return 1
    key = argv[0]
    # mailbox=True registers on the Almanac and is reachable from ASI:One.
    agent = build_specialist(key, mailbox=True)
    print(f"{key} address: {address_of(SPECIALISTS[key]['seed'])}")
    agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
