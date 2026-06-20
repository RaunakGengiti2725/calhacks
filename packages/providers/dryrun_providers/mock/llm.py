"""Mock LLM provider.

Stands in for ASI:One. `parse_request` extracts structured fields from a plain-
English request with deterministic heuristics (regex). `summarize` writes a
researcher-facing paragraph from already-computed facts — it never invents
numbers, it only narrates what it is handed.
"""

from __future__ import annotations

import re

from dryrun_providers.base import LLMProvider

_AA = "ACDEFGHIKLMNPQRSTVWY"
_SEQ_RE = re.compile(rf"\b[{_AA}]{{20,}}\b")
_BUDGET_RE = re.compile(
    r"(?:\$\s?(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:dollars|usd|bucks))",
    re.IGNORECASE,
)
_COUNT_RE = re.compile(
    r"(\d{1,3})\s*(?:candidates?|variants?|designs?|sequences?)", re.IGNORECASE
)
_GOAL_HINTS = (
    "thermal stability", "thermostability", "stability", "binding affinity",
    "binding", "expression", "solubility", "activity", "catalytic", "folding",
    "aggregation",
)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


class MockLLMProvider(LLMProvider):
    def parse_request(self, text: str) -> dict:
        t = text or ""

        seq_match = _SEQ_RE.search(t.upper())
        seed_sequence = seq_match.group(0) if seq_match else None

        budget = None
        bm = _BUDGET_RE.search(t)
        if bm:
            budget = _num(bm.group(1) or bm.group(2))

        candidate_count = None
        cm = _COUNT_RE.search(t)
        if cm:
            candidate_count = int(cm.group(1))

        goal = None
        low = t.lower()
        for hint in _GOAL_HINTS:
            if hint in low:
                # capture a short verb phrase around the hint if present
                m = re.search(
                    rf"((?:improve|increase|enhance|boost|maximize|raise|reduce|lower|"
                    rf"decrease)\s+[\w\s]*?{re.escape(hint)})",
                    low,
                )
                goal = (m.group(1) if m else hint).strip()
                break

        return {
            "seed_sequence": seed_sequence,
            "goal": goal,
            "budget": budget,
            "candidate_count": candidate_count,
        }

    def summarize(self, report_facts: dict) -> str:
        f = report_facts
        selected = f.get("designs_selected", 0)
        total = f.get("designs_total", 0)
        spend = f.get("spend", 0.0)
        budget = f.get("budget", 0.0)
        expected = f.get("expected_distinct_successes", 0.0)
        naive_expected = f.get("naive_expected_distinct_successes", 0.0)
        cps = f.get("cost_per_success", 0.0)
        dollars_match = f.get("dollars_naive_needs_to_match")
        goal = f.get("goal") or "the stated goal"

        uplift = (expected / naive_expected) if naive_expected > 1e-9 else 1.0

        parts = [
            f"From {total} candidate designs toward {goal}, DryRun recommends "
            f"synthesizing {selected} — spending ${spend:,.0f} of your ${budget:,.0f} "
            f"budget.",
            f"That portfolio is expected to cover about {expected:.1f} distinct "
            f"functional approaches (diversity-adjusted), versus {naive_expected:.1f} "
            f"for a naive 'buy the highest-scoring' strategy at the same budget — "
            f"roughly {uplift:.1f}x more, because DryRun spreads risk across "
            f"uncorrelated regions of sequence space instead of buying near-"
            f"duplicates that fail together.",
        ]
        if dollars_match is not None:
            parts.append(
                f"To match DryRun's expected successes, the naive strategy would "
                f"need about ${dollars_match:,.0f}."
            )
        if cps > 0:
            parts.append(f"Effective cost per expected success: ${cps:,.0f}.")
        return " ".join(parts)
