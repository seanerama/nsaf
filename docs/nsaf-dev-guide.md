# NSAF Development Guide

> **Prompt:** "I'm adding a feature to NSAF. Read this file for the current architecture, file map, and deployment process, then help me implement what I'll describe."

## Access

- **Dev machine:** Local at `/home/smahoney/projects/nsaf`
- **Production server:** `ssh smahoney@100.110.222.42` (Tailscale) — `/home/smahoney/nsaf`
- **GitHub:** `https://github.com/seanerama/nsaf` (public, branch: master)
- **EC2 (Coolify):** `ssh ubuntu@34.207.137.224` — runs Coolify for promoted app deployments

## Architecture

Three processes + shared SQLite:

```
Flask App (Python :5000) ←→ SQLite (nsaf.db) ←→ Orchestrator (Node.js)
                                    ↑
                            Idea Generator (Python, cron)
```

- **Orchestrator** — queue processing, Claude Code session spawning, state polling, stall detection, app launching, evening digest
- **Flask App** — Webex bot (20+ commands), idea selection web UI, QA review pages, ngrok tunnel
- **Idea Generator** — morning cron, 3 AI providers (OpenAI/Gemini/Anthropic) with temperature tiers
- **Shared SQLite** — accessed by all three via WAL mode (Node: better-sqlite3, Python: sqlite3 with thread-local connections)

## Project Types

| Type | Pipeline | Spawned With | Completion Signal |
|------|----------|-------------|-------------------|
| `app` | SDD (architect → plan → build → test → deploy) | `/sdd:start --from architect` | STATE.md deployer role complete |
| `studyws` | StudyWS (scope → research → write → diagrams → guide → slides → podcast) | `/sws:start` | `textbook.md` exists in output dir |

## File Map

### Orchestrator (`orchestrator/src/`)
| File | Responsibility |
|------|---------------|
| `index.js` | Main loop — dequeue, allocate ports, scaffold, spawn, monitor, digest |
| `db.js` | SQLite CRUD — 6 tables: ideas, idea_history, projects, queue, ports, config |
| `queue.js` | Queue state queries — pause check, concurrency limit |
| `ports.js` | Port allocation in 10-port batches from 5020-5999 |
| `postgres.js` | Per-app PostgreSQL database create/drop via execFileSync |
| `scaffolder.js` | Project dir setup — vision doc, .env, git init, MCP tool detection |
| `spawner.js` | Claude Code session launch — prompt building, API key stripping, exit handling, app auto-launch, StudyWS resume detection |
| `poller.js` | STATE.md parsing — extracts phase/role/progress, detects completion |
| `stall.js` | Stall detection — time-based for apps, process-check for studyws |
| `completion.js` | Marks projects deployed-local, extracts URL from build log |
| `notify.js` | Webex notifications via REST API (stall, completion, promotion) |
| `digest.js` | Evening summary email via Resend |
| `promotion.js` | Detects promoted status, spawns Render deploy (legacy) |
| `app-launcher.js` | Auto-start apps — tries start.sh, backend+frontend, server/index.js, npm start |
| `dockerize.js` | Dockerfile generation — detects project structure, patches CORS/static serving |

### Flask App (`flask-app/`)
| File | Responsibility |
|------|---------------|
| `app.py` | Flask entry, ngrok tunnel setup, Webex webhook registration |
| `routes/select.py` | GET/POST `/select` — idea selection UI |
| `routes/review.py` | GET/POST `/review/<slug>` — QA checklist |
| `routes/webex.py` | POST `/webex/webhook` — strips bot mention, routes to command handler |
| `bot/commands.py` | **All Webex commands** (~1500 lines) — this is where most features are added |
| `bot/notifications.py` | Outbound Webex messages from Flask context |

### Idea Generator (`idea-generator/`)
| File | Responsibility |
|------|---------------|
| `generate.py` | Cron entry — loads preferences, calls providers, stores ideas, sends email |
| `prompt.py` | Prompt builder + temperature tier definitions per provider |
| `providers/openai_gen.py` | GPT-4o — 4 temp tiers |
| `providers/gemini_gen.py` | Gemini 2.5 Flash — 4 temp tiers |
| `providers/anthropic_gen.py` | Claude Sonnet — 4 temp tiers (max 1.0) |
| `dedup.py` | History tracking for idea deduplication |
| `email_sender.py` | Morning email formatting + Resend delivery |

### Shared (`shared/`)
| File | Responsibility |
|------|---------------|
| `db.py` | Python SQLite interface — thread-safe, WAL mode, ALLOWED_PROJECT_FIELDS whitelist |
| `config.py` | Preferences.md parser |

### Config
| File | Purpose |
|------|---------|
| `preferences.md` | Categories, exclusions, tech stack, complexity, design — controls idea generation |
| `config/animation-strategy.md` | SVG/CSS animation requirements for StudyWS guides |
| `.env` | All secrets and config (gitignored) |
| `detected-tools.json` | Auto-generated MCP tool inventory (gitignored) |

## Webex Bot Commands (all in `bot/commands.py`)

**Build:** status, pause, pause all, resume, skip, restart, rebuild, modify
**Ideas:** ideas, idea, queue, generate
**StudyWS:** sws
**Lifecycle:** promote, demote, archive, delete, gitpush, export
**App Control:** stop, start, stopall
**Troubleshooting:** debug
**Monitoring:** system, tokens, help

## Adding a New Webex Command

1. Add handler function in `flask-app/bot/commands.py`:
   ```python
   def cmd_mycommand(arg):
       """Description."""
       # arg is everything after the command name
       return "Response text (markdown supported)"
   ```

2. Register in the `handlers` dict (line ~25):
   ```python
   "mycommand": cmd_mycommand,
   ```

3. Update help text in `cmd_help()` (bottom of file)

4. For file attachments, return a dict:
   ```python
   return {"text": "Here's the file", "files": ["/tmp/export.csv"]}
   ```

## Adding a New Project Type

1. Add type handling in `orchestrator/src/index.js` `processQueue()` — skip ports/DB if not needed
2. Add prompt building in `orchestrator/src/spawner.js` — detect `project_type` and build appropriate prompt
3. Add completion detection in spawner exit handler — what signals "done"?
4. Add stall detection in `orchestrator/src/stall.js` — how to detect stuck builds?
5. Add creation command in `flask-app/bot/commands.py`

## Database Schema

```sql
projects: id, idea_id, slug (UNIQUE), status, project_type ('app'|'studyws'),
          port_start, port_end, db_name, project_dir,
          sdd_phase, sdd_active_role, sdd_progress,
          deployed_url, render_url, last_state_change, stall_alerted,
          started_at, completed_at, created_at

ideas: id, date, source, rank, name, description, category, complexity,
       suggested_stack, temperature, tier, selected, created_at

queue: id, project_id, position, created_at
ports: port_start (PK), port_end, project_id, allocated_at
config: key (PK), value
idea_history: id, name, description, date
```

To add a column: `ALTER TABLE projects ADD COLUMN myfield TEXT DEFAULT '';`
Also add to `ALLOWED_PROJECT_FIELDS` in `shared/db.py` and schema in `orchestrator/src/db.js`.

## Deployment Workflow

### Code change → deploy:

```bash
# 1. Make changes locally
cd /home/smahoney/projects/nsaf

# 2. Commit and push
git add <files>
git commit -m "description"
git push

# 3. SSH to server and pull
ssh smahoney@100.110.222.42 "cd ~/nsaf && git pull"

# 4. Restart affected service(s)
# For Flask/bot changes:
ssh smahoney@100.110.222.42 bash <<'EOF'
pkill -f "flask-app/app.py"; pkill -f ngrok; sleep 3
cd ~/nsaf && nohup venv/bin/python flask-app/app.py > /tmp/nsaf-flask.log 2>&1 &
EOF

# For orchestrator changes:
ssh smahoney@100.110.222.42 bash <<'EOF'
pkill -f "node orchestrator/src/index.js"; sleep 2
cd ~/nsaf && nohup node orchestrator/src/index.js > /tmp/nsaf-orch.log 2>&1 &
EOF

# For idea-generator changes: no restart needed (runs via cron or on-demand)
```

### DB migration (adding column):
```bash
ssh smahoney@100.110.222.42 "sqlite3 ~/nsaf/nsaf.db 'ALTER TABLE projects ADD COLUMN myfield TEXT DEFAULT \"\";'"
```

### Quick one-liner deploy:
```bash
git push && ssh smahoney@100.110.222.42 "cd ~/nsaf && git pull && pkill -f 'flask-app/app.py'; pkill -f ngrok; pkill -f 'node orchestrator/src/index.js'; sleep 3; cd ~/nsaf; nohup node orchestrator/src/index.js > /tmp/nsaf-orch.log 2>&1 &; nohup venv/bin/python flask-app/app.py > /tmp/nsaf-flask.log 2>&1 &"
```

## Promote Pipeline (app → production)

When user sends `promote <slug>` in Webex:
1. Generate Dockerfile (auto-detect project structure)
2. Generate README.md
3. Push to GitHub (`seanerama/<slug>`, public)
4. Create Coolify app (Dockerfile build pack)
5. Set env vars in Coolify (DATABASE_URL, PORT, NODE_ENV, CORS_ORIGIN)
6. Trigger Coolify deploy
7. Add Cloudflare Tunnel route (`https://localhost:443` with noTLSVerify → Traefik)
8. Add Cloudflare DNS CNAME (`<slug>.seanmahoney.ai` → tunnel)
9. Update project status to "promoted"

## External Integrations

| Service | Config | Used By |
|---------|--------|---------|
| Webex | WEBEX_BOT_TOKEN, WEBEX_OWNER_PERSON_ID | Flask bot + orchestrator notifications |
| ngrok | NGROK_AUTHTOKEN | Flask app (tunnel for Webex webhook) |
| Resend | RESEND_API_KEY | Idea generator (morning email) + orchestrator (digest) |
| Coolify | COOLIFY_API_URL, COOLIFY_API_TOKEN, COOLIFY_PROJECT_UUID, COOLIFY_SERVER_UUID | Promote command |
| Cloudflare | CF_ACCOUNT_ID, CF_TUNNEL_ID, CF_TUNNEL_TOKEN, CF_DNS_TOKEN, CF_ZONE_ID | Promote/demote commands |
| GitHub | `gh` CLI auth | Promote + gitpush commands |
| PostgreSQL | POSTGRES_HOST/PORT/USER/PASSWORD | App database provisioning |
| Perplexity | PERPLEXITY_API_KEY (in MCP config) | StudyWS research stage |
| OpenAI/Gemini/Anthropic | API keys in .env | Idea generation only (stripped from Claude Code env) |

## Testing

```bash
# Node.js
cd orchestrator && node --test tests/

# Python
PYTHONPATH=. python3 -m pytest shared/tests/ idea-generator/tests/

# Flask
PYTHONPATH=.:flask-app python3 -m pytest flask-app/tests/
```
