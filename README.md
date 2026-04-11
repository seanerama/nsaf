<p align="center">
  <img src="nsaf-banner-image.jpg" alt="Nightshift AutoFoundry" width="100%">
</p>

# Nightshift AutoFoundry (NSAF)

A personal content factory that autonomously generates web applications, textbooks, and study guides. Every morning, AI surfaces curated app ideas. You pick the ones you like. NSAF handles the rest — speccing, coding, testing, and deploying each one without human intervention. Need a textbook instead? Just tell the Webex bot a topic and NSAF generates a complete learning package.

## How It Works

### Apps
1. **Morning ideas** — A cron job generates 30 app ideas from three AI models (OpenAI, Gemini, Anthropic) using tiered temperature sampling for a mix of practical and experimental concepts
2. **You select** — Browse the ideas in a web UI or via Webex and pick the ones you want built
3. **NSAF builds** — The orchestrator queues your selections and spawns autonomous Claude Code sessions that build each app through a full spec-driven development pipeline
4. **You review** — Finished apps are deployed locally with a QA checklist. Approve, modify, or rebuild them through the Webex chatbot
5. **Promote to production** — Approved apps are deployed via Coolify to `*.seanmahoney.ai` subdomains

### Textbooks & Study Guides (StudyWS Integration)
1. **You name a topic** — Send `sws <topic>` via Webex, optionally with a source URL (PDF, syllabus, exam blueprint)
2. **NSAF generates** — Spawns a Claude Code session running the [StudyWS](https://www.npmjs.com/package/studyws) pipeline
3. **Full learning package** — Produces a textbook, interactive HTML study guides with quizzes, slide descriptions, and a podcast prompt

```
sws Kubernetes Networking
sws CCDE v3 Exam Prep https://example.com/exam-topics.pdf --chapters 15 --level advanced
sws Machine Learning --chapters 8 --level beginner
```

#### StudyWS Output
```
output/<topic-slug>/
├── config.json           # Topic metadata
├── outline.json          # Chapter hierarchy
├── research/             # Perplexity research per chapter
├── chapters/             # Written chapters with diagrams
├── textbook.md           # Full textbook with table of contents
├── guides/               # Interactive HTML study guides (open in browser)
├── slides.md             # Slide descriptions for deck creation
└── podcast-prompt.md     # Podcast generation prompt
```

Each study guide is a self-contained HTML file with pre/post quizzes, score comparison, key points, and Mermaid diagrams — open directly in a browser.

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
┌─────────────────────────────────────────────────────┐
│                  Ubuntu Server                       │
│                                                      │
│  Cron ──→ Idea Generator (Python)                   │
│              ↓                                       │
│  Flask App (Python)                                  │
│    ├── Idea selection UI                             │
│    ├── QA review pages                               │
│    └── Webex chatbot ──→ sws <topic> (StudyWS)      │
│              ↓ (SQLite)                              │
│  Orchestrator (Node.js)                              │
│    ├── Queue manager                                 │
│    ├── Port allocator (5020-5999)                    │
│    ├── PostgreSQL provisioner                        │
│    ├── Session spawner (Claude Code)                 │
│    │   ├── App builds (/sdd:start)                   │
│    │   └── Content builds (/sws:start)               │
│    ├── State monitor + stall detection               │
│    ├── App auto-launcher                             │
│    └── Evening digest                                │
│              ↓                                       │
│  Apps: local deploy ──→ Coolify (on promotion)       │
│  Content: output/ directory with textbook + guides   │
└─────────────────────────────────────────────────────┘
```

NSAF is three processes communicating through a shared SQLite database:
- **Orchestrator** (Node.js) — manages the build queue, spawns coding sessions (SDD for apps, StudyWS for content), monitors progress, auto-launches finished apps
- **Flask App** (Python) — serves the idea selection UI, QA pages, and Webex bot
- **Idea Generator** (Python) — runs daily via cron to produce ideas and send the morning email

## Prerequisites

- Ubuntu 22.04+ server
- Node.js 20+
- Python 3.12+
- PostgreSQL 15+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) — installed, authenticated, and licensed
- [StudyWS](https://www.npmjs.com/package/studyws) — installed globally for content generation (`npm i -g studyws && sws setup`)
- Webex bot token (create at [developer.webex.com](https://developer.webex.com))
- [ngrok](https://ngrok.com) account (for Webex webhook tunneling)
- [Resend](https://resend.com) account for email delivery
- API keys for OpenAI, Google (Gemini), and Anthropic
- [Perplexity API key](https://www.perplexity.ai/settings/api) (for StudyWS research, ~$0.006/query)

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
| **Cloudflare** | Infrastructure | Tunnel routes + DNS for `*.seanmahoney.ai` subdomains |
| **GitHub** | Code Hosting | Repository management and PR creation |
| **Perplexity** | Research | StudyWS uses Perplexity MCP for chapter research |

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
| `COOLIFY_API_URL` | Coolify instance URL for promotion deployments | — |

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
| `pause all` | Emergency stop: pause queue + kill all active Claude sessions |
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

### Content Generation (StudyWS)

| Command | Description |
|---------|-------------|
| `sws <topic>` | Generate a textbook + study guides for a topic |
| `sws <url>` | Generate from a PDF/document (exam blueprint, syllabus, etc.) |
| `sws <topic> --chapters 12 --level beginner` | With options |
| `sws <topic> <url> --level advanced` | Topic + source document + options |

### Lifecycle

| Command | Description |
|---------|-------------|
| `promote <slug>` | Push to GitHub + deploy via Coolify to `*.seanmahoney.ai` |
| `demote <slug>` | Remove from Coolify, revert to local-only |
| `archive <slug>` | Stop running locally, release ports, keep files |
| `delete <id or slug> [...]` | Permanently delete one or more projects |
| `gitpush <slug>` | Push a project to a new public GitHub repo |
| `export` | Download a CSV of all ideas and projects |

### App Control

| Command | Description |
|---------|-------------|
| `stop <slug>` | Stop a running local app |
| `start <slug>` | Start a stopped local app |
| `stopall` | Stop all running local apps |

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

## Project Types

NSAF handles two types of projects through the same queue:

| Type | Trigger | Build Pipeline | Output |
|------|---------|---------------|--------|
| **App** | `queue <id>` or idea selection UI | SDD (Spec-Driven DevOps) | Running web app on allocated port |
| **StudyWS** | `sws <topic>` | StudyWS pipeline | Textbook, study guides, slides, podcast prompt |

App projects get port allocation, PostgreSQL provisioning, and auto-launching. StudyWS projects skip all infrastructure and just produce files.

## Project Lifecycle

Each project moves through these states:

```
queued → building → deployed-local → reviewing → promoted
                                   → archived
                                   → scrapped
```

- **queued** — Waiting for a build slot
- **building** — Claude Code session running (SDD pipeline for apps, StudyWS for content)
- **deployed-local** — Build complete. Apps are running on the server. Content is in the output directory.
- **reviewing** — You're testing it with the QA checklist
- **promoted** — Deployed via Coolify to `*.seanmahoney.ai`
- **archived** — Stopped locally, ports released, files preserved
- **scrapped** — Rejected and cleaned up

## Promotion Pipeline

When you run `promote <slug>`, NSAF automates the full deployment:

1. **Dockerfile generated** — Auto-detects project structure (fullstack-split, server-only, static)
2. **Server patched** — Fixes CORS, adds static file serving, adjusts ports for production
3. **README generated** — App name, description, live URL, setup instructions
4. **Pushed to GitHub** — Creates public repo at `seanerama/<slug>`
5. **Coolify app created** — Connects repo, sets Dockerfile build pack
6. **Environment variables set** — DATABASE_URL, PORT, NODE_ENV, CORS_ORIGIN
7. **Build triggered** — Coolify builds Docker image and starts container
8. **Cloudflare tunnel route added** — `<slug>.seanmahoney.ai` → Traefik (HTTPS, noTLSVerify)
9. **DNS CNAME created** — Points subdomain to tunnel

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
│   │   ├── spawner.js      # Claude Code session launcher (SDD + StudyWS)
│   │   ├── app-launcher.js # Auto-start apps after build completion
│   │   ├── dockerize.js    # Dockerfile generation for promotion
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
│   ├── bot/                # command handlers (20+ commands), notifications
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
│   ├── restart-apps.sh     # Watchdog — restarts dead apps + fixes stuck builds
│   └── register-webhook.sh # Webex webhook registration
├── systemd/                # Service files (templated)
├── static/                 # Banner + icon images
├── preferences.md          # What to build — the single control surface
├── recovery-plan.md        # Ops runbook + disaster recovery
├── codebase-map.html       # Interactive architecture diagram
└── .env.example            # All configuration documented
```

## License

Private project — not for redistribution.
