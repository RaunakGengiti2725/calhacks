# DryRun

**An autonomous pre-synthesis experiment-design engine for molecular biology.**

Before a biologist can test a new protein design in a lab, they must physically
manufacture its DNA — paying a vendor (~$0.09 / base pair, a few hundred dollars
per construct) and waiting two to three weeks. Most designs fail: across decades
of structural-biology data, only about a third of engineered proteins express and
fold well enough to be usable. And when researchers hedge by ordering many
near-identical variants of one idea, they *concentrate* rather than reduce risk —
those similar designs share hidden weaknesses and fail together.

**DryRun answers one question with real financial weight: given a fixed budget,
which subset of candidate protein designs should a researcher actually pay to
synthesize?** It is a marketplace of specialized AI agents you talk to in plain
English, forming a cost-minimizing cascade: a cheap sequence-viability model
scores every candidate, only the survivors go to an expensive structure-prediction
model, real synthesis costs are estimated, and a portfolio optimizer selects the
set of designs that maximizes expected successful experiments per dollar while
deliberately diversifying across sequence space so failures are uncorrelated.

The result: roughly twice the expected successful experiments from the same
budget — and you can see exactly why before committing a dollar.

---

## The prime directive

No feature hard-depends on an external API at its call site. Every external
service (ASI:One, Evo 2, AlphaFold2, vendor pricing) is reached through a provider
interface with two implementations — a **Mock** (instant synthetic data, no
network) and a **Live** (real API). One environment variable selects which,
globally:

```
DRYRUN_MODE=mock   # default — runs fully, no credentials
DRYRUN_MODE=live   # real APIs; each falls back to mock on any failure
```

The entire application runs, demos, and passes tests in mock mode with zero keys.

---

## Quick start (mock mode, no API keys)

```bash
make install     # install Python deps (uv); auto-fetches Python 3.11
make test        # run the core + provider test suite (no network)
make demo        # run the full cascade end to end, print the JSON report
make web         # start the Next.js frontend (the demo centerpiece)
```

> Requires [`uv`](https://docs.astral.sh/uv/) and Node 18+. `make install` does
> not need any credentials.

---

## Architecture

```
packages/
  core/        dryrun_core        pure domain logic (optimizer, cost, scoring, embedding) — fully unit-tested
  providers/   dryrun_providers   the provider abstraction: base ABCs, mock/, live/, factory (DRYRUN_MODE switch)
  agents/      dryrun_agents      thin uAgents + the uagents-free in-process cascade + CLI
apps/
  api/         FastAPI gateway the frontend talks to (also bridges to agents)
  web/         Next.js + TypeScript + Tailwind frontend (Mol* 3D, funnel, cost chart, sequence-space map)
```

**The non-wrapper core** is the portfolio optimizer (`dryrun_core/optimizer.py`).
It is *not* "rank by score, take top N." It solves a budget-constrained,
diversity-aware selection problem with a **submodular coverage objective** and a
cost-aware **greedy** algorithm. Budget-constrained submodular maximization is
NP-hard; the greedy approach carries a provable **(1 − 1/e) ≈ 0.63** approximation
guarantee (cardinality case; the budget variant is guarded with the
best-single-affordable element to keep the bound honest). `naive_topn_select` is
provided alongside purely so the UI can show the contrast.

---

## The agents

*(Phase 4 — addresses filled in after Agentverse registration.)*

| Agent | Standalone value | Live backend |
|-------|------------------|--------------|
| Design Generator | "propose N variants of this protein toward this goal" | Evo 2 NIM (generative) |
| Sequence Fitness | "score how biologically plausible this sequence is" | Evo 2 NIM (likelihood) |
| Fold Risk | "will this protein fold, and where is it structurally fragile?" | AlphaFold2 NIM |
| Synthesis Cost | "what will this construct cost to manufacture?" | vendor pricing (model in core) |
| Portfolio Optimizer | "given these scored options and my budget, what should I actually buy?" | none (real decision logic) |
| Reporting | "turn an analysis into a shareable researcher-facing report" | none |
| Orchestrator | the agent a researcher chats with; parses intent, drives the cascade | ASI:One |

---

## Modes & configuration

See [`.env.example`](.env.example) for every variable. Copy it to `.env` and set
keys only if you want `DRYRUN_MODE=live`.

---

## Roadmap (Phase 6)

- Optional Payment Protocol (FET) gating the expensive Fold Risk agent (shared-infra economics / monetization).
- Calibration of success probabilities against real experimental outcome datasets.
- Additional structure models (OpenFold2, ESMFold) selectable per request.
- Multi-objective optimization (expected successes vs novelty vs cost on a Pareto frontier).
- A "what-if budget slider" that re-runs the optimizer live.
- Real vendor pricing APIs in the Synthesis Cost live provider.

---

## Build status

- [x] Phase 0 — scaffold & contracts (models, provider ABCs, factory, clean install)
- [ ] Phase 1 — core domain logic, fully tested
- [ ] Phase 2 — mock providers + in-process cascade CLI (`make demo`)
- [ ] Phase 3 — FastAPI gateway + Next.js frontend (mock mode)
- [ ] Phase 4 — cascade stages as uAgents (Chat Protocol)
- [ ] Phase 5 — live providers, Agentverse registration & discovery
