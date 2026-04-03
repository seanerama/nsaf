<p align="center">
  <img src="nsaf-banner-image.jpg" alt="Nightshift AutoFoundry" width="100%">
</p>

# Nightshift AutoFoundry (NSAF)

A personal app factory that generates, builds, and deploys web applications autonomously. Every morning, AI surfaces curated app ideas. You pick the ones you like. NSAF handles the rest — speccing, coding, testing, and deploying each one without human intervention.

## How It Works

1. **Morning ideas** — A cron job generates 30 app ideas from three AI models (OpenAI, Gemini, Anthropic) using tiered temperature sampling for a mix of practical and experimental concepts
2. **You select** — Browse the ideas in a web UI or via Webex and pick the ones you want built
3. **NSAF builds** — The orchestrator queues your selections and spawns autonomous Claude Code sessions that build each app through a full spec-driven development pipeline
4. **You review** — Finished apps are deployed locally with a QA checklist. Approve, modify, or rebuild them through the Webex chatbot
5. **Promote to production** — Approved apps are deployed to Render with a single command

## Idea Generation & Temperature Tiers

Each morning, NSAF calls three AI providers (OpenAI, Gemini, Anthropic) to generate 10 ideas each — 30 total. Instead of using a single temperature, each provider makes 4 calls at escalating temperatures to produce a spectrum from safe to wild:

| Tier | Temperature | Ideas | Style |
|------|------------|-------|-------|
| **Conservative** | 0.2–0.3 | 3 | Safe, proven concepts — the kind of app you'd find in a "top 10 tools" list |
| **Balanced** | 0.5–0.7 | 3 | Moderately creative — practical but with a twist |
| **Creative** | 0.8–1.0 | 2 | Pushing boundaries — unusual combinations and novel approaches |
| **Experimental** | 1.0–1.4 | 2 | Wild, unexpected — the ideas that might be brilliant or might be crazy |

Each batch is told to avoid duplicating ideas from earlier tiers, previous days, and the other providers. Temperature ranges are tuned per provider (Anthropic caps at 1.0, OpenAI and Gemini go higher).

Ideas are tagged with their tier so you can filter and sort by creativity level when selecting what to build.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Ubuntu Server                   │
│                                                  │
│  Cron ──→ Idea Generator (Python)               │
│              ↓                                   │
│  Flask App (Python)                              │
│    ├── Idea selection UI                         │
│    ├── QA review pages                           │
│    └── Webex chatbot                             │
│              ↓ (SQLite)                          │
│  Orchestrator (Node.js)                          │
│    ├── Queue manager                             │
│    ├── Port allocator (5020-5999)                │
│    ├── PostgreSQL provisioner                    │
│    ├── Session spawner (Claude Code)             │
│    ├── State monitor + stall detection           │
│    ├── App auto-launcher                         │
│    └── Evening digest                            │
│              ↓                                   │
│  Local deployments ──→ Render (on promotion)     │
└─────────────────────────────────────────────────┘
```

NSAF is three processes communicating through a shared SQLite database:
- **Orchestrator** (Node.js) — manages the build queue, spawns coding sessions, monitors progress, auto-launches finished apps
- **Flask App** (Python) — serves the idea selection UI, QA pages, and Webex bot
- **Idea Generator** (Python) — runs daily via cron to produce ideas and send the morning email

## Prerequisites

- Ubuntu 22.04+ server
- Node.js 20+
- Python 3.12+
- PostgreSQL 15+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) — installed, authenticated, and licensed
- Webex bot token (create at [developer.webex.com](https://developer.webex.com))
- [ngrok](https://ngrok.com) account (for Webex webhook tunneling)
- [Resend](https://resend.com) account for email delivery
- API keys for OpenAI, Google (Gemini), and Anthropic

## Quick Start

```bash
# Clone
git clone <repo-url> /opt/nsaf
cd /opt/nsaf

# Configure
cp .env.example .env
# Edit .env — fill in all API keys and settings

# Run setup (detects MCP tools, installs deps, configures services)
bash scripts/setup.sh

# Start services
sudo systemctl start nsaf-orchestrator nsaf-flask

# Test idea generation
source venv/bin/activate
python idea-generator/generate.py --dry-run
```

## MCP Tool Integrations

NSAF detects MCP tools configured in your Claude Code environment and automatically uses them during builds. Run `scripts/detect-tools.sh` to see what's available, or check `detected-tools.json` after setup.

| Tool | Category | How NSAF Uses It |
|------|----------|-----------------|
| **Render** | Deployment | Deploys promoted apps to Render via `mcp__render__*` tools |
| **PixelLab** | Art Generation | Generates pixel art sprites, characters, tiles, and animations for games |
| **Leonardo AI** | Art Generation | Generates illustrations, backgrounds, icons, and UI art |
| **Cloudflare** | Infrastructure | Available for DNS, Workers, R2, and other Cloudflare services |
| **GitHub** | Code Hosting | Repository management and PR creation |

Games automatically get PixelLab sprites + Leonardo backgrounds. Non-game apps get Leonardo for optional hero images and branding. Only tools detected in your Claude Code config are referenced in build prompts — if you don't have PixelLab configured, builds won't try to use it.

To add a new MCP tool, configure it in Claude Code (`~/.claude.json`), then re-run:
```bash
bash scripts/detect-tools.sh
```

## Configuration

### Environment Variables

All configuration lives in `.env`. See `.env.example` for the full list with descriptions.

Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `NSAF_CONCURRENCY` | Max simultaneous build sessions | `2` |
| `NSAF_PORT_RANGE_START` | Start of port range for local deployments | `5020` |
| `NSAF_PORT_RANGE_END` | End of port range | `5999` |
| `NSAF_STALL_TIMEOUT_MINUTES` | Minutes before a build is flagged as stalled | `30` |
| `NSAF_PROJECTS_DIR` | Where generated projects are stored | `./projects` |
| `NGROK_AUTHTOKEN` | ngrok auth token for Webex webhook tunneling | — |

### Preferences

Edit `preferences.md` to control what NSAF builds. Categories can include sub-examples to guide the AI:

```markdown
## Idea Categories
- Sports & Activity: stats trackers, fantasy tools, pickup game organizers
- Education & Learning: flashcard builders, quiz generators, study group tools
- Finance & Money: budget visualizers, bill splitters, expense categorizers

## Exclusions
- gambling
- adult content

## Tech Stack
- Frontend: React preferred
- Backend: Node.js preferred
- Database: PostgreSQL (required — provisioned automatically)
- CSS: Tailwind preferred

## Design
- Tone: modern, clean
- Mobile First: yes

## Complexity Range
- Minimum: medium
- Maximum: high

## Daily Quota
30
```

No code changes needed — just edit the file and the next generation will reflect your preferences.

## Webex Bot Commands

Control Nightshift AutoFoundry from your phone or desktop through Webex. Works in direct messages or spaces (tag the bot with `@Nightshift-AutoFoundry`).

### Build Management

| Command | Description |
|---------|-------------|
| `status` | Queue depth, active builds, deployed apps with URLs |
| `pause` | Stop pulling new projects from the queue |
| `resume` | Resume pulling from the queue |
| `skip <slug>` | Remove a project and mark as scrapped |
| `restart <slug>` | Re-queue a stalled or failed project |
| `rebuild <slug> [notes]` | Wipe and rebuild from scratch — notes are injected into the vision doc |
| `modify <slug> <changes>` | Spawn Claude to make specific changes to an existing build |

### Ideas

| Command | Description |
|---------|-------------|
| `ideas` | List today's ideas (paginated, 10 per page) |
| `ideas 2` | Page 2 of ideas |
| `ideas openai` | Filter ideas by provider |
| `idea <id>` | Detailed view of a specific idea with build status |
| `queue <id>` | Add an idea to the build queue |
| `generate` | Trigger a fresh round of idea generation |

### Lifecycle

| Command | Description |
|---------|-------------|
| `promote <slug>` | Deploy a locally-tested app to Render |
| `demote <slug>` | Remove from Render, revert to local-only |
| `archive <slug>` | Stop running locally, release ports, keep files |
| `delete <id or slug> [...]` | Permanently delete one or more projects |
| `gitpush <slug>` | Push a project to a new public GitHub repo |
| `export` | Download a CSV of all ideas and projects |

### Troubleshooting

| Command | Description |
|---------|-------------|
| `debug <slug> <problem>` | Spawn Claude to diagnose and fix a deployed app |

### Monitoring

| Command | Description |
|---------|-------------|
| `system` | CPU, memory, disk, active Claude sessions, project counts |
| `tokens [hours]` | Build activity and costs for the last N hours (default 24) |
| `help` | Show all available commands |

## Project Lifecycle

Each app moves through these states:

```
queued → building → deployed-local → reviewing → promoted
                                   → archived
                                   → scrapped
```

- **queued** — Waiting for a build slot
- **building** — Claude Code session is running the full SDD pipeline
- **deployed-local** — Build complete, app running on the server for QA
- **reviewing** — You're testing it with the QA checklist
- **promoted** — Deployed to Render
- **archived** — Stopped locally, ports released, files preserved
- **scrapped** — Rejected and cleaned up

## Notifications

- **Webex** (real-time) — Stall alerts, build completions, deployment confirmations
- **Email** (scheduled) — Morning idea list with selection link, evening digest with the day's results

## Running Tests

```bash
# Node.js tests (orchestrator)
cd orchestrator && node --test tests/

# Python tests (shared + idea generator)
PYTHONPATH=. python3 -m pytest shared/tests/ idea-generator/tests/

# Flask tests
PYTHONPATH=.:flask-app python3 -m pytest flask-app/tests/

# Cross-language integration
PYTHONPATH=. python3 -m pytest tests/
```

## Project Structure

```
nsaf/
├── orchestrator/           # Node.js — queue, spawning, monitoring
│   ├── src/
│   │   ├── index.js        # Main loop + systemd entry point
│   │   ├── db.js           # SQLite interface
│   │   ├── queue.js        # Queue management
│   │   ├── ports.js        # Port allocation
│   │   ├── postgres.js     # Per-app database provisioning
│   │   ├── scaffolder.js   # Project directory setup + vision doc generation
│   │   ├── spawner.js      # Claude Code session launcher
│   │   ├── app-launcher.js # Auto-start apps after build completion
│   │   ├── poller.js       # STATE.md polling
│   │   ├── stall.js        # Stall detection
│   │   ├── completion.js   # Build completion handler
│   │   ├── notify.js       # Webex notifications (direct API)
│   │   ├── digest.js       # Evening digest via Resend
│   │   └── promotion.js    # Render promotion via MCP
│   └── tests/
├── flask-app/              # Python — web UI + Webex bot
│   ├── app.py              # Flask entry + ngrok/webhook setup
│   ├── routes/             # select, review, webex webhook
│   ├── bot/                # command handlers, notifications
│   ├── templates/          # HTML templates
│   └── tests/
├── idea-generator/         # Python — multi-model idea generation
│   ├── generate.py         # Cron entry point
│   ├── prompt.py           # Prompt construction + temperature tiers
│   ├── dedup.py            # Idea history for deduplication
│   ├── email_sender.py     # Morning email via Resend
│   ├── providers/          # openai, gemini, anthropic
│   └── tests/
├── shared/                 # Python — shared SQLite + config
│   ├── db.py               # Thread-safe SQLite interface
│   └── config.py           # Preferences parser + env vars
├── scripts/
│   ├── setup.sh            # First-time server setup
│   ├── detect-tools.sh     # MCP tool detection
│   ├── restart-apps.sh     # Watchdog — restarts dead apps
│   └── register-webhook.sh # Webex webhook registration
├── systemd/                # Service files (templated)
├── static/                 # Banner + icon images
├── preferences.md          # What to build — the single control surface
├── recovery-plan.md        # Ops runbook + disaster recovery
└── .env.example            # All configuration documented
```

## License

Private project — not for redistribution.
