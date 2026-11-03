# GTM Mesh (AI-MZ)

Claude agents that run go-to-market work for each client, for example **Greta** and **Psyler**. The agents research the market, find leads, draft outreach and content, and send a weekly report. A person approves everything before it goes out.

## What runs

| Agent | What it does | Output |
|---|---|---|
| `profile` | Researches a new client from their website and fills in their profile | `clients/<slug>.yaml` |
| `research` | Weekly market brief: positioning, competitors, where they show up in search, buyer pain, 5 hooks | brief in the database |
| `leads` | Finds companies that fit each funnel, checks the evidence, finds the decision-maker | accounts + contacts |
| `outbound` | Writes a personal email and LinkedIn note for the best new accounts | **review queue** (never sent automatically) |
| `content` | Writes LinkedIn posts, X threads, Reddit posts, blog outlines and directory listings | review queue |
| `report` | Weekly traction update: pipeline, spend, what needs a human | `output/<slug>/reports/` |

- **Weekly cycle** (Mondays): research (if older than 7 days), then leads, outbound, content, report
- **Daily top-up** (Tue to Fri): a small batch of leads and outbound
- Each client has its own database (`output/<slug>/mesh.db`), so client data never mixes
- Each agent run has a spend cap (`max_usd_per_agent_run`, default $8) and is logged with tokens, searches and estimated cost

## Quick start

```bash
cd gtm-mesh
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...
```

Fill in each client's profile (the agent researches them and writes the YAML):

```bash
gtm-mesh new greta --website https://<greta-site> --sender "Aroob Manzoor" --notes "who they sell to, offer, warm leads"
```

```bash
gtm-mesh new psyler --website https://<psyler-site> --sender "Aroob Manzoor" --notes "..."
```

- Then open `clients/greta.yaml` and `clients/psyler.yaml` and fix anything that's off (funnels, proof points, sign-off)

Run the first full cycle for both:

```bash
gtm-mesh cycle all
```

Review and approve:

```bash
gtm-mesh review greta
```

```bash
gtm-mesh approve greta 3 4 7
```

## Everyday commands

| Command | Use |
|---|---|
| `gtm-mesh list` | List clients |
| `gtm-mesh cycle <slug>` / `cycle all` | Full weekly run (`--mode daily` for the top-up) |
| `gtm-mesh run <slug> <agent> --count N` | Run one agent, e.g. `run psyler leads --count 40` |
| `gtm-mesh status <slug>` | Pipeline, drafts and spend for the last 7 days |
| `gtm-mesh review <slug>` | Write the review queue to `output/<slug>/review/` (Markdown + CSV) |
| `gtm-mesh approve / reject / sent <slug> <ids>` | Move drafts through review |
| `gtm-mesh mark <slug> <domain> replied` | Log replies, meetings and wins so the weekly report reflects them |

## Run it on the Mac Mini

```bash
./deploy/install_mac.sh
```

- Creates the venv, installs the package, and creates `.env` (paste the client's API key in)
- Schedules the weekly run (Mon 6:37am) and the daily top-up (Tue to Fri 7:13am) with launchd
- Logs go to `gtm-mesh/logs/`
- Turn off sleep on the Mini so scheduled runs fire

## Guardrails

- Nothing is sent or posted automatically; drafts go to the review queue
- Agents only save facts they checked during the run and include the source link
- Emails are only saved if they're published publicly; agents never guess email patterns
- Reddit posts are written to be useful on their own, with no pitch and no DMs
- If the spend cap is hit, the agent stops and keeps what it already saved

## Tests

```bash
pytest
```

- Offline tests use a fake Claude client, so no key or network is needed

## How it's built

- Python + the official Anthropic SDK (`anthropic`), using the SDK tool runner
- Model `claude-opus-5-5` with adaptive thinking; effort is set per client (`models.effort`)
- Server-side web search and web fetch for research; custom tools write to SQLite
- Server-side refusal fallback is on (`fallbacks: "default"`)
- Prompt caching is on; the client profile is in a stable system prompt so it caches across runs
- Change the model, effort or spend cap per client in the `models:` block of their YAML
