# Daily-Brief

A personal, profile-aware, **on-demand news-catch-up engine**, delivered as a Claude Code
skill package (no server). It researches the latest news on the topics you care about —
through the lens of a chosen **profile** (e.g. *AI Engineer*, *Realtor*, *Parent*) — remembers
what you've already seen, and produces three outputs per run:

- an **interactive HTML brief** (collapsible topics, search, source/date filters, mark-as-read),
- a **markdown summary**, and
- a **NotebookLM-style podcast script**.

Every item carries a **"why this matters"** line framed through the active profile.

## How it works

- **Slash commands** orchestrate runs: `/brief:run`, `/brief:topic`, `/brief:setup`,
  `/brief:status`, `/brief:help`.
- A **Python engine + `brief` CLI** does all deterministic work (profiles, history, dedup,
  rendering) — no AI calls.
- **In-session Claude sub-agents** (your subscription) do the research/framing/podcast writing;
  the **Perplexity MCP** (paid Sonar Pro) does open-web research. No Anthropic API key needed.
- Data is plain **markdown on local disk** under `data/` (gitignored).

```
Slash command ─► fan out sub-agents (Perplexity MCP + Claude site research + framing + podcast)
              └► brief CLI (profiles · history · dedup · render) ─► data/briefs/<profile>/<ts>/
```

## Install

Full steps in [`sdd-output/deploy-instruct.md`](sdd-output/deploy-instruct.md). In short:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env          # set PERPLEXITY_API_KEY
ln -s "$(pwd)/commands/brief" ~/.claude/commands/brief   # install slash commands
brief init                    # create data/ + the General profile
brief status
```

Also configure the **Perplexity MCP server** in your Claude Code settings (it reads
`PERPLEXITY_API_KEY`).

## Documentation

- **[User Guide](docs/user-guide.md)** — concepts, your first brief, everyday use, reading a brief.
- **[Profiles Guide](docs/profiles.md)** — author and tune profiles.
- **[CLI Reference](docs/cli-reference.md)** — every `brief` command.

## Commands

| Command | What it does |
|---------|--------------|
| `/brief:run [profile]` | Sweep a profile's sources for the latest → full brief. |
| `/brief:topic <topic> [profile] [sources]` | Research one topic → brief; surfaces what's new since last look. |
| `/brief:setup [profile]` | Create or edit a profile (role/lens with topics + sources). |
| `/brief:status` | Show profiles, history counts, and last runs. |
| `/brief:help` | List commands + current state. |

The `brief` CLI mirrors the deterministic half (`brief init|status|profile|history|dedup|assemble|render|podcast-prompt|history-from-run|kb-append`).

## Data layout

```
data/
  profiles/<slug>/
    reference.md        # profile config: topics + typed sources
    history.md          # append-only log (drives dedup)
    knowledge-base.md   # accumulated learnings (written v1, queried v2)
  briefs/<slug>/<YYYY-MM-DD-HHMM>/
    brief.html  summary.md  podcast-script.md  run.json  run.log
```

Define a profile by hand from [`assets/profile-template.md`](assets/profile-template.md) (see
[`assets/profile-sample.md`](assets/profile-sample.md)) or via `/brief:setup`.

## Scope

**v1 (now):** both triggers; multiple profiles + built-in General; Perplexity + Claude research;
per-profile dedup/history with "also covered by X on DATE"; separate history + knowledge-base
files; interactive HTML + markdown + podcast *script*; per-item profile framing.

**Deferred to v2+:** YouTube ingestion (type kept in the model), podcast **audio**, knowledge-base
**querying**, in-app **scheduling**, an optional FastAPI wrapper, and paywalled/credentialed sources.

See [`sdd-output/project-plan.md`](sdd-output/project-plan.md) for the full architecture.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

v0.1.0 — feature-complete for the v1 scope above.
