"""Static registry of DryRun agents: fixed seeds (→ deterministic addresses),
ports, discovery keywords, and descriptions.

Pure data — no `uagents` import — so it can be read on the light install (e.g. to
print addresses in docs). Seeds are fixed so every run yields the same Almanac
address, which is what the README documents and what the orchestrator falls back
to for discovery.
"""

from __future__ import annotations

# Each specialist maps to one handler in dryrun_agents.shared.handlers.
SPECIALISTS: dict[str, dict] = {
    "design_generator": {
        "seed": "dryrun-design-generator-seed-v1",
        "port": 8101,
        "handler": "generation_handler",
        "keywords": ["protein design", "variant generation", "mutagenesis", "Evo 2", "sequence design"],
        "description": "Proposes N candidate protein variants of a seed sequence toward a stated design goal.",
    },
    "sequence_fitness": {
        "seed": "dryrun-sequence-fitness-seed-v1",
        "port": 8102,
        "handler": "fitness_handler",
        "keywords": ["protein", "sequence viability", "fitness scoring", "Evo 2", "biological plausibility"],
        "description": "Scores how biologically plausible a protein sequence is — a cheap, whole-pool viability filter.",
    },
    "fold_risk": {
        "seed": "dryrun-fold-risk-seed-v1",
        "port": 8103,
        "handler": "fold_handler",
        "keywords": ["protein structure", "AlphaFold2", "fold prediction", "pLDDT confidence", "misfolding"],
        "description": "Predicts whether a protein folds and where it is structurally fragile (per-residue pLDDT + misfold flag).",
    },
    "synthesis_cost": {
        "seed": "dryrun-synthesis-cost-seed-v1",
        "port": 8104,
        "handler": "cost_handler",
        "keywords": ["gene synthesis", "DNA synthesis cost", "cloning", "construct cost", "Twist Bioscience"],
        "description": "Estimates the synthesis-plus-cloning cost to manufacture a DNA construct from a protein sequence.",
    },
    "portfolio_optimizer": {
        "seed": "dryrun-portfolio-optimizer-seed-v1",
        "port": 8105,
        "handler": "optimizer_handler",
        "keywords": ["portfolio optimization", "submodular", "budget allocation", "diversification", "selection"],
        "description": "Given scored designs and a budget, selects the diversity-aware subset that maximizes expected distinct successes per dollar.",
    },
    "reporting": {
        "seed": "dryrun-reporting-seed-v1",
        "port": 8106,
        "handler": "reporting_handler",
        "keywords": ["report generation", "protein analysis report", "results payload", "visualization"],
        "description": "Turns an analysis into a single, complete, researcher-facing report payload.",
    },
}

ORCHESTRATOR: dict = {
    "seed": "dryrun-orchestrator-seed-v1",
    "port": 8100,
    "keywords": ["DryRun", "protein design portfolio", "pre-synthesis experiment design", "synthesis budget"],
    "description": "Chat with this to decide, given a budget, which candidate protein designs to actually pay to synthesize.",
}
