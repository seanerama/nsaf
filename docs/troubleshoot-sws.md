# Troubleshoot StudyWS Builds in NSAF

> **Prompt:** "I'm troubleshooting a StudyWS build in NSAF. Read this file for context, then help me diagnose and fix the issue I'll describe."

## Access

- **NSAF server:** `ssh smahoney@100.110.222.42` (Tailscale IP)
- **NSAF directory:** `/home/smahoney/nsaf`
- **Projects directory:** `/home/smahoney/nsaf/projects/`
- **SQLite DB:** `/home/smahoney/nsaf/nsaf.db`
- **GitHub repo:** `https://github.com/seanerama/nsaf`

## Architecture Overview

NSAF has three processes communicating via shared SQLite:

1. **Orchestrator** (Node.js) — `orchestrator/src/index.js` — manages queue, spawns Claude Code sessions, monitors progress
2. **Flask App** (Python) — `flask-app/app.py` — Webex bot + web UI, ngrok tunnel for webhooks
3. **Idea Generator** (Python) — `idea-generator/generate.py` — cron-triggered, generates app/content ideas

StudyWS projects use `project_type = 'studyws'` in the DB. They differ from app builds:
- **No port allocation** — content doesn't run as a server
- **No PostgreSQL provisioning** — no database needed
- **No app scaffolding** — just creates project dir + `studyws-config.json`
- **Spawns with `/sws:start`** instead of `/sdd:start --from architect`
- **Completion detected by `textbook.md`** existence, not STATE.md
- **Resume logic** — detects partial output and skips completed pipeline stages

## StudyWS Pipeline Stages

```
/sws:start → /sws:scope → /sws:research → /sws:write → /sws:diagrams → /sws:guide → /sws:slides → /sws:podcast
```

Each stage spawns parallel sub-agents. Output goes to `projects/<slug>/output/<topic-slug>/`:

```
output/<topic>/
├── config.json          # Topic metadata
├── outline.json         # Chapter hierarchy
├── research/chapter-*.md  # Perplexity research per chapter
├── chapters/chapter-*.md  # Written chapters with mermaid diagrams
├── textbook.md          # Full assembled textbook
├── guides/chapter-*.html  # Interactive HTML study guides with SVG animations
├── slides.md            # Slide descriptions
└── podcast-prompt.md    # Podcast generation prompt
```

## Key Files for StudyWS

| File | What it does |
|------|-------------|
| `orchestrator/src/spawner.js` | Builds the Claude prompt, detects resume state, writes CLAUDE.md |
| `orchestrator/src/stall.js` | StudyWS-aware stall detection (checks for claude process + output dir) |
| `orchestrator/src/index.js` | Queue processing — skips ports/DB for studyws type |
| `flask-app/bot/commands.py` | `cmd_sws()` — parses topic/URL/flags, creates config, queues project |
| `config/animation-strategy.md` | Animation requirements injected as CLAUDE.md for guide sub-agents |
| `projects/<slug>/studyws-config.json` | Topic, chapters, level, notes, source_url |
| `projects/<slug>/CLAUDE.md` | Animation strategy auto-written by spawner for sub-agent inheritance |

## Checking if a Webex Command Worked

```bash
# 1. Check Flask received the webhook
tail -20 /tmp/nsaf-flask.log

# 2. Check the project was created in DB
sqlite3 ~/nsaf/nsaf.db "SELECT slug, status, project_type FROM projects WHERE slug LIKE '%your-topic%';"

# 3. Check the queue
sqlite3 ~/nsaf/nsaf.db "SELECT p.slug FROM queue q JOIN projects p ON q.project_id = p.id ORDER BY q.position;"

# 4. Check orchestrator picked it up
tail -20 /tmp/nsaf-orch.log

# 5. Check Claude is running
ps aux | grep claude | grep -v grep
```

## Checking Build Progress

```bash
SLUG="sws-your-topic"

# What exists in output?
find ~/nsaf/projects/$SLUG/output -type f 2>/dev/null | head -20

# Which stages completed?
ls ~/nsaf/projects/$SLUG/output/*/research/   # Research done?
ls ~/nsaf/projects/$SLUG/output/*/chapters/   # Writing done?
ls ~/nsaf/projects/$SLUG/output/*/textbook.md # Textbook assembled?
ls ~/nsaf/projects/$SLUG/output/*/guides/     # Guides generated?
ls ~/nsaf/projects/$SLUG/output/*/slides.md   # Slides done?
ls ~/nsaf/projects/$SLUG/output/*/podcast-prompt.md # Podcast done?

# Check animations in guides
for g in ~/nsaf/projects/$SLUG/output/*/guides/*.html; do
  echo "$(basename $g) — SVGs: $(grep -c '<svg' $g), @keyframes: $(grep -c '@keyframes' $g), Replay: $(grep -ci 'replay' $g)"
done

# Build log (may be empty — claude output goes to sub-agents)
tail -30 ~/nsaf/projects/$SLUG/build.log
```

## Common Issues

### Build stalled — no claude process running
```bash
# Check if process died
ps aux | grep claude | grep -v grep | grep "$SLUG"

# Re-queue for resume (spawner detects partial output automatically)
sqlite3 ~/nsaf/nsaf.db "
UPDATE projects SET status='queued', stall_alerted=0 WHERE slug='$SLUG';
DELETE FROM queue WHERE project_id=(SELECT id FROM projects WHERE slug='$SLUG');
INSERT INTO queue (project_id, position) SELECT id, (SELECT COALESCE(MAX(position),0)+1 FROM queue) FROM projects WHERE slug='$SLUG';
"
```

### Guides missing animations
- Check `projects/$SLUG/CLAUDE.md` exists with animation strategy
- If missing, spawner had `writeFileSync` error — check `/tmp/nsaf-orch.log`
- Verify `config/animation-strategy.md` exists in NSAF root

### Perplexity research not working
- Check `PERPLEXITY_API_KEY` is in `~/nsaf/.env`
- Check Perplexity MCP is in both `~/.claude.json` AND `~/.claude/settings.json`:
  ```json
  "perplexity-mcp": {
    "command": "npx",
    "args": ["-y", "perplexity-mcp"],
    "env": {"PERPLEXITY_API_KEY": "your-key"}
  }
  ```

### API keys leaking to Claude Code (billing issue)
- Spawner strips `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` from Claude env
- Only Perplexity key is passed through (needed for MCP)

### Pipeline completed but status still "building"
- Watchdog cron (`restart-apps.sh` every 2 min) checks for completed studyws builds
- Manual fix: `sqlite3 ~/nsaf/nsaf.db "UPDATE projects SET status='deployed-local', sdd_phase='complete', sdd_progress=100 WHERE slug='$SLUG';"`

## Process Management

```bash
# Restart orchestrator
pkill -f "node orchestrator/src/index.js"; sleep 2
cd ~/nsaf && nohup node orchestrator/src/index.js > /tmp/nsaf-orch.log 2>&1 &

# Restart Flask + ngrok
pkill -f "flask-app/app.py"; pkill -f ngrok; sleep 3
cd ~/nsaf && nohup venv/bin/python flask-app/app.py > /tmp/nsaf-flask.log 2>&1 &

# Pull latest code
cd ~/nsaf && git pull

# Kill all claude sessions (emergency)
pkill -f "claude.*dangerously"
```
