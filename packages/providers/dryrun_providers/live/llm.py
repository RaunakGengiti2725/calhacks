"""Live LLM provider — ASI:One (OpenAI-Chat-Completions compatible).

Used by the orchestrator for natural-language intent parsing and the plain-English
report summary. Every external call is isolated in `_chat`, and every public
method falls back to the mock provider on any error or missing key, so the demo
path never hard-fails.
"""

from __future__ import annotations

import json
import logging
import os
import re

from dryrun_providers import provenance
from dryrun_providers.base import LLMProvider
from dryrun_providers.config import is_strict
from dryrun_providers.mock.llm import MockLLMProvider

logger = logging.getLogger("dryrun.live.llm")

_STAGE = "llm"

_PARSE_SYSTEM = (
    "You extract structured fields from a protein-engineering request. Return ONLY "
    "a JSON object with keys: seed_sequence (string or null, an amino-acid sequence), "
    "goal (string or null), budget (number or null, USD), candidate_count (integer or "
    "null). Do not include any prose."
)
_SUMMARY_SYSTEM = (
    "You are a scientific writing assistant. Given a JSON object of already-computed "
    "facts about a protein-design portfolio analysis, write 2-4 concise, plain-English "
    "sentences for a researcher. Use ONLY the numbers provided; never invent values."
)


def _extract_json(text: str) -> dict:
    """Isolated response parser: pull the first JSON object out of the LLM reply."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return json.loads(text[start : end + 1])


class LiveLLMProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.getenv("ASI_ONE_API_KEY")
        if not api_key:
            raise RuntimeError("ASI_ONE_API_KEY not set")
        from openai import OpenAI  # imported lazily so mock mode never needs it

        self._client = OpenAI(
            base_url=os.getenv("ASI_ONE_BASE_URL", "https://api.asi1.ai/v1"), api_key=api_key
        )
        self._model = os.getenv("ASI_ONE_MODEL", "asi1-mini")
        self._mock = MockLLMProvider()

    def _chat(self, system: str, user: str, max_tokens: int = 800) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def parse_request(self, text: str) -> dict:
        try:
            fields = _extract_json(self._chat(_PARSE_SYSTEM, text))
            provenance.mark(_STAGE, provenance.LIVE, "asi:one parse_request")
            return {
                "seed_sequence": fields.get("seed_sequence"),
                "goal": fields.get("goal"),
                "budget": fields.get("budget"),
                "candidate_count": fields.get("candidate_count"),
            }
        except Exception as exc:  # noqa: BLE001 — graceful fallback unless strict
            if is_strict():
                raise
            logger.warning("ASI:One parse failed (%s); using mock", exc)
            provenance.mark(_STAGE, provenance.FALLBACK, str(exc))
            return self._mock.parse_request(text)

    def summarize(self, report_facts: dict) -> str:
        try:
            out = self._chat(_SUMMARY_SYSTEM, json.dumps(report_facts), max_tokens=400).strip()
            if not out:
                raise ValueError("empty summary from ASI:One")
            provenance.mark(_STAGE, provenance.LIVE, "asi:one summarize")
            return out
        except Exception as exc:  # noqa: BLE001 — graceful fallback unless strict
            if is_strict():
                raise
            logger.warning("ASI:One summarize failed (%s); using mock", exc)
            provenance.mark(_STAGE, provenance.FALLBACK, str(exc))
            return self._mock.summarize(report_facts)
