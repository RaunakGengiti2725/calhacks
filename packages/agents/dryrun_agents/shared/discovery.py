"""Runtime discovery of the specialist agents.

The orchestrator prefers to LOCATE specialists at runtime (Agentverse keyword
search) rather than only hardcoding addresses, but always falls back to the
deterministic config addresses so the demo is reliable. The Agentverse search
request/parse is isolated in `_search_agentverse`; verify it against the current
Agentverse API. With no AGENTVERSE_API_KEY it goes straight to the config
fallback.
"""

from __future__ import annotations

import logging
import os

import requests

from dryrun_agents.shared.agent_config import SPECIALISTS
from dryrun_agents.shared.build_agent import specialist_addresses

logger = logging.getLogger("dryrun.discovery")

_AGENTVERSE_SEARCH = os.getenv(
    "AGENTVERSE_SEARCH_URL", "https://agentverse.ai/v1/search/agents"
)


def _search_agentverse(keywords: list[str], api_key: str) -> str | None:
    """ISOLATED Agentverse keyword search → best-matching agent address (or None)."""
    resp = requests.post(
        _AGENTVERSE_SEARCH,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"search_text": " ".join(keywords), "limit": 1},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    agents = body.get("agents") or body.get("results") or []
    if agents:
        first = agents[0]
        return first.get("address") or first.get("agent_address")
    return None


def resolve_specialist_addresses() -> dict[str, str]:
    """Discover specialist addresses, falling back to deterministic config addresses.

    Per-specialist: if Agentverse search finds a match, use it; otherwise use the
    fixed-seed address. So discovery degrades gracefully, key by key.
    """
    config = specialist_addresses()
    api_key = os.getenv("AGENTVERSE_API_KEY")
    if not api_key:
        return config

    resolved: dict[str, str] = {}
    for key, cfg in SPECIALISTS.items():
        try:
            found = _search_agentverse(cfg["keywords"], api_key)
            resolved[key] = found or config[key]
            if found:
                logger.info("discovered %s via Agentverse: %s", key, found)
        except Exception as exc:  # noqa: BLE001 — fall back to the known address
            logger.warning("Agentverse discovery for %s failed (%s); using config", key, exc)
            resolved[key] = config[key]
    return resolved
