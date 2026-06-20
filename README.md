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

# the graphical product (two terminals):
make api         # FastAPI gateway on :8000 (drives the cascade)
make web         # Next.js frontend on :3000 (the demo centerpiece)
```

> Requires [`uv`](https://docs.astral.sh/uv/) and Node 18+. Nothing here needs any
> credentials. The frontend ships a bundled mock report, so `make web` renders the
> full report even if the API isn't running — it just falls back to the demo result.

**The 3D structure viewer** defaults to a dependency-free, WebGL-optional backbone
renderer (rotating CA trace colored by the AlphaFold pLDDT scale, mutations marked)
so the demo never shows a blank viewport. Full Mol* molecular graphics is wired in
as an optional enhancement — set `NEXT_PUBLIC_USE_MOLSTAR=1` to enable it; it only
takes over once it has actually painted a structure.

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
NP-hard. The honest guarantees: plain greedy gives **(1 − 1/e) ≈ 0.63** under a
*cardinality* constraint; under a *budget* constraint, `max(greedy, best single)`
gives only **(1 − 1/√e) ≈ 0.39**, so to recover the full **(1 − 1/e) ≈ 0.63** the
solver seeds the greedy from every feasible subset of size ≤ 3 (Sviridenko /
Khuller-Moss-Naor partial enumeration) — cheap here because the optimizer runs
only on the few designs that survive the viability + fold filters.
`naive_topn_select` is provided alongside purely so the UI can show the contrast.

---

## The agents

Six specialist uAgents + an orchestrator, each implementing the Agentverse Chat
Protocol so it is independently messageable and discoverable. Each passes the
"standalone-useful to a stranger" test. Addresses below are deterministic (derived
from fixed seeds), so they are stable across runs.

| Agent | Standalone value | Address (deterministic) | Live backend |
|-------|------------------|-------------------------|--------------|
| Orchestrator | chat to decide what to synthesize under a budget | `agent1qfq02ucduq4davsl0n9u9s8r854lm27f9gee3gfz88at9z25e4jm6zs8xnj` | ASI:One |
| Design Generator | "propose N variants of this protein toward this goal" | `agent1qv2kw5n0qq2sde3jpq4ywc7f62tdq4lqnya59d79che7lx8mkrs8ju6yepn` | Evo 2 NIM (generative) |
| Sequence Fitness | "score how biologically plausible this sequence is" | `agent1qt56g95rf3c4y439sur4uplc8rd0l5448vkljx0x932fyhzs7qnqv56nuuh` | Evo 2 NIM (likelihood) |
| Fold Risk | "will this protein fold, and where is it structurally fragile?" | `agent1qwsysq6zqz4a2tvldgvhvup8tg4r8e3chx09p3cyyl7wk5ln000sx2tu5w6` | AlphaFold2 NIM |
| Synthesis Cost | "what will this construct cost to manufacture?" | `agent1qvpqskgud5fp4n7utgq3unzx66xyc892ga2l2zhvrm8lsmv5fgtzqy9nxly` | vendor pricing (model in core) |
| Portfolio Optimizer | "given these scored options and my budget, what should I actually buy?" | `agent1q2e56a258jjfwzdyute7y7ly362vxuv4dn3y4cjrqqfa0gmlxwwpq92vpec` | none (real decision logic) |
| Reporting | "turn an analysis into a shareable researcher-facing report" | `agent1qfksdhz2yu9g6x6cjy42w04dt4tw6rrdaw8p0v3h2sj6e3a2f4mf5kq68w5` | none |

```bash
make install-agents   # adds the uagents framework
make agents           # run all agents together in one Bureau (local, no network)
# or run one specialist standalone (mailbox -> reachable from ASI:One):
uv run --extra agents python -m dryrun_agents.run_specialist sequence_fitness
uv run --extra agents python -m dryrun_agents.run_orchestrator
```

The orchestrator coordinates the specialists over the Chat Protocol
(`send_and_receive`); if any specialist is unreachable it falls back to the
in-process cascade, so a demo never depends on all agents being live at once.

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
- [x] Phase 1 — core domain logic, fully tested (39 tests, no network)
- [x] Phase 2 — mock providers + in-process cascade CLI (`make demo`)
- [x] Phase 3 — FastAPI gateway + Next.js frontend (mock mode): summary metrics,
      cost-comparison chart, screening funnel, 3D structure + pLDDT confidence
      track, sequence-space scatter, candidate table
- [x] Phase 4 — six specialist uAgents + orchestrator on the Chat Protocol,
      coordinated via `send_and_receive` with an in-process fallback (verified
      end to end in a local Bureau)
- [ ] Phase 5 — live providers (ASI:One, Evo 2 NIM, AlphaFold2 NIM), Agentverse
      registration & runtime discovery
