# DryRun — going live (API keys & ASI:One agents)

This guide takes DryRun from the no-keys mock demo to **real external APIs**, then
registers the agents so they're discoverable and chattable from **ASI:One**.

The architecture already separates "the world" from the logic: every external
service is behind a provider with a Mock and a Live implementation, switched by one
env var. You don't change code to go live — you paste keys into `.env` and flip
`DRYRUN_MODE=live`.

> **Honesty by design.** When a live call fails it falls back to mock *and the UI
> shows that per stage* (the colored "live / fallback / mock / local" pills under
> the report title). It never presents fallback data as real. To make any silent
> substitution impossible, set `DRYRUN_STRICT=1` and a failed live call raises
> instead of falling back.

---

## 0. What is and isn't an external API

Three honest categories — "real" does **not** mean "every box calls a server":

| Stage | Live backend | Category |
|-------|--------------|----------|
| Summary / intent parsing | **ASI:One** (`api.asi1.ai`) | real external API |
| Structure / fold risk | **AlphaFold2** (NVIDIA NIM) | real external API |
| Viability scoring | **Evo 2** (NVIDIA NIM, DNA) | real external API |
| Variant generation | **Evo 2** (NVIDIA NIM, DNA) | real external API |
| Synthesis cost | in-process cost model (standard vendor rates) | real **local** algorithm |
| Portfolio optimizer | submodular solver in `dryrun_core` | real **local** algorithm |

The optimizer and cost model are genuine algorithms, not mock data — no public
vendor exposes an unauthenticated DNA-synthesis quoting API, so cost uses standard
per-bp/cloning rates in real math (shown as `local` in the UI, never `mock`).

> **Evo 2 caveat (read this).** Evo 2 is a **genomic (DNA)** model, not a protein
> model. DryRun back-translates each protein to DNA (`live/_dna.py`) before calling
> Evo 2, and translates results back. This bridge is **matched to NVIDIA's
> documented schema but not yet verified against a live key.** Once you have an
> NVIDIA key, sanity-check the generation/viability output; the per-call mock
> fallback keeps the app working if the schema has drifted.

---

## 1. Quick start (mock, no keys)

```bash
make install      # Python deps (uv)
make test         # 58+ tests, no network
make api          # FastAPI gateway on :8000   (terminal 1)
make web          # Next.js frontend on :3000  (terminal 2)
```

`.env` already exists (copied from `.env.example`) with `DRYRUN_MODE=mock`.

---

## 2. Get the API keys

### 2a. ASI:One (LLM) — required for the live orchestrator summary

1. Go to **https://asi1.ai** and sign in.
2. Open the **Developer** area → **API Keys** → **Create API Key**.
3. Copy the key and paste it into `.env`:
   ```
   ASI_ONE_API_KEY=sk_...your_key...
   ```
`ASI_ONE_BASE_URL` and `ASI_ONE_MODEL` (`asi1-mini`) defaults are already correct.

### 2b. NVIDIA NIM (Evo 2 + AlphaFold2) — required for live biology

1. Go to **https://build.nvidia.com** and sign in (free NVIDIA Developer account).
2. Open any biology model (e.g. **AlphaFold2** or **arc / evo2-40b**) and click
   **Get API Key** / **Generate API Key**. The key is prefixed **`nvapi-`**.
3. Paste it into `.env`:
   ```
   NVIDIA_API_KEY=nvapi-...your_key...
   ```
The hosted biology base (`https://health.api.nvidia.com/v1`) and the AlphaFold2 URL
are already set. Keep `DRYRUN_FOLD_CAP=4` — AlphaFold2 takes minutes per sequence.

> Free-tier NIM has rate/credit limits. If a call is throttled, DryRun records a
> `fallback` for that stage (visible in the UI) instead of breaking.

**On your first keyed Evo 2 run, sanity-check two things** (both degrade to mock
cleanly if off, so nothing breaks — but this is what "correct" looks like):

1. **Viability layer key.** `live/viability.py` requests `output_layers:
   ["output_layer"]` to get logits. If your NIM names that layer differently (the
   docs also list `embedding`, `decoder.final_norm`, `decoder.layers.N.mixer`),
   the parse will fail and you'll see `viability: fallback`. Fix is one line in
   `_score_one`.
2. **Generation shape.** Evo 2 generates a *DNA continuation*, which is translated
   back to protein — so live variants will often differ in length from the seed
   and show no neat point-mutations (unlike the mock generator). That's expected
   for a real generative model, not a bug.

### 2c. Agentverse — only for registering/discovering the agents (section 5)

1. Go to **https://agentverse.ai** and sign in.
2. **Profile → API Keys → New API Key**, copy it into `.env`:
   ```
   AGENTVERSE_API_KEY=...your_key...
   ```
Optional: the in-process cascade and the website work without it. It's used for
runtime agent **discovery** (keyword search) and is handy for the agent flow below.

---

## 3. Flip to live

In `.env`:
```
DRYRUN_MODE=live
```
Then:
```bash
make stop          # free ports if the mock servers are up
make api           # terminal 1
make web           # terminal 2
```
Open **http://localhost:3000**, run an analysis, and watch the provenance pills:
green **live** = real API; amber **fallback** = a live call failed (read the
tooltip); blue **local** = real in-process model.

CLI equivalent:
```bash
make live          # one-off live cascade, prints the JSON report
# or
DRYRUN_MODE=live uv run dryrun --natural "stabilize my protein, ~$500, 15 variants"
```

---

## 4. Prove it's actually live (no hidden mock)

- **Per-stage pills** in the UI — anything not green isn't a real API result.
- **Strict mode** — the strongest guarantee:
  ```
  DRYRUN_STRICT=1
  DRYRUN_MODE=live
  ```
  Now any live failure (missing key, bad schema, throttling) **raises** instead of
  falling back. If the cascade completes, every external stage was genuinely live.
  The API returns a clear `502` with the reason instead of silently mocking.
- **Backend mode/health:** `curl http://localhost:8000/health` →
  `{"status":"ok","mode":"live","strict":false}`.

---

## 5. Create the ASI:One agents on Agentverse (the "fetch website" steps)

DryRun ships six specialist uAgents + an orchestrator, each already implementing
the **Chat Protocol** required by ASI:One (see
`packages/agents/dryrun_agents/shared/build_agent.py`: `mailbox=True`,
`publish_agent_details=True`, `agent.include(proto, publish_manifest=True)`). You
don't write agent code — you run them with a mailbox and link them on the website.

### 5a. Install the agent framework and run an agent with a mailbox

```bash
make install-agents
# run one specialist standalone (reachable from ASI:One):
uv run --extra agents python -m dryrun_agents.run_specialist sequence_fitness
# or the orchestrator:
uv run --extra agents python -m dryrun_agents.run_orchestrator
```
On startup the agent prints its **address** and an **Agent Inspector URL**
(`https://agentverse.ai/inspect/?...`). Keep this process running.

### 5b. Link it on agentverse.ai (the website steps)

1. Sign in at **https://agentverse.ai**.
2. Open the **Inspector URL** the agent printed (or **Agents → Local Agents**).
3. Click **Connect → Mailbox** and follow the prompts. This binds the running
   agent to Agentverse's mailroom so it's reachable even between requests.
4. Click **Agent Profile** and set a clear **name, handle, and description**
   (these power ASI:One search — the descriptions in `agent_config.py` are good
   starting text). Publish/save.
5. Repeat 5a–5b for each agent you want individually discoverable, or run the whole
   set locally with `make agents` (one Bureau; great for the cascade, but the
   mailbox/website link above is what exposes an agent to ASI:One).

### 5c. Chat from ASI:One

1. With the agent connected, click **Chat with Agent** on Agentverse, or
2. Go to **https://asi1.ai**, and in chat ask for what the agent does (e.g. "score
   how plausible this protein sequence is: …"). ASI:One discovers registered,
   chat-protocol agents and routes to them.

> The orchestrator coordinates the specialists over the Chat Protocol and falls
> back to the in-process cascade if any specialist is unreachable — so a demo never
> depends on all agents being live at once.

> **Heads-up:** Agentverse's Inspector UI labels shift over time. If a button name
> differs, the flow is the same: *run with `mailbox=True` → open the printed
> Inspector link → Connect as Mailbox → edit the profile for search.* Current
> reference: https://innovationlab.fetch.ai/resources/docs/examples/chat-protocol/asi-compatible-uagents

---

## 6. Still seeing mock? Checklist

1. Is `DRYRUN_MODE=live` in `.env`? (`curl localhost:8000/health` to confirm.)
2. Restart the API after editing `.env` (it's read at startup).
3. A shell `export DRYRUN_MODE=mock` overrides `.env` — unset it.
4. Turn on `DRYRUN_STRICT=1` — the raised error names the exact failing provider.
5. Check the API logs: each fallback logs a warning with the upstream reason.
6. NVIDIA: key must be `nvapi-` and have NIM credits; biology host is
   `health.api.nvidia.com` (not `integrate.*`).
