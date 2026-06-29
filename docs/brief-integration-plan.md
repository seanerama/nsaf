# NSAF × Daily-Brief Integration — Implementation Plan

> **Audience:** subagents implementing this feature. Each numbered step is self-contained and can be assigned independently.
> **Read first:** the **Reference** section before starting any step.

## 1. Goal

Add a new NSAF `project_type='brief'` that drives the **Daily-Brief** Claude Code skill package (separately installed at `$NSAF_BRIEF_HOME`) from Webex. Mirrors the `sws` pattern (one-shot orchestrator job, no ports/DB) but with these differences:

- **Persistent profiles + history live in `$NSAF_BRIEF_HOME/data/`**, not in `projects/<slug>/`. Each NSAF row is just an audit record for one run.
- **Two slash commands** to invoke: `/brief:run <profile>` (sweep) and `/brief:topic <topic> --profile <slug>` (single topic).
- **NotebookLM post-step** converts the brief's `summary.md` into a `podcast.mp3` (NotebookLM-style two-host podcast).
- **Webex setup flow** mirrors the `vision` multi-turn Q&A (`flask-app/bot/vision.py`) so users can author profiles without SSH'ing in. Power-user shortcut: paste a fenced YAML profile body in the same `brief setup <slug>` message.
- **Completion** = a new dated subdir under `$NSAF_BRIEF_HOME/data/briefs/<slug>/<TS>/` containing `brief.html`, `summary.md`, AND `podcast.mp3`.
- **On completion** the orchestrator posts a Webex message and attaches all three files (HTML + summary md + podcast mp3).

**Out of scope (v2+):** website promotion (`promote brief`), in-app scheduling, automatic profile creation from an existing knowledge base.

---

## 2. Reference

### 2.1 NSAF patterns to mirror

| Concern | Existing reference |
|---|---|
| Skip-ports-and-DB for content pipelines | `orchestrator/src/index.js:65-108` (the `if (projectType === 'studyws' \|\| projectType === 'story')` branches) |
| `project_type` branching in spawner | `orchestrator/src/spawner.js:44, 47 (studyws), 180 (story)` |
| Per-type stall detection | `orchestrator/src/stall.js:37, 41 (studyws), 72 (story)` |
| Project creation + enqueue from Webex | `cmd_sws` at `flask-app/bot/commands.py:1862` |
| Multi-turn Q&A state machine | `cmd_vision` at `flask-app/bot/commands.py:422`; full engine in `flask-app/bot/vision.py` and DB helpers (`vision_insert`, `vision_get`, `vision_update`, `vision_list`) imported at `commands.py:19` |
| Webex notify + file attachment | `orchestrator/src/notify.js` — read first to confirm attachment API; also `bot/notifications.py` for Flask-side equivalent |

### 2.2 Daily-Brief surface

- **Repo:** `https://github.com/<user>/Daily-Brief` (local dev clone at `/home/smahoney/projects/Daily-Brief/`)
- **Server install path:** `$NSAF_BRIEF_HOME` (kept separate from `~/nsaf/`, e.g. `~/Daily-Brief/`)
- **Slash commands** (live in `$NSAF_BRIEF_HOME/commands/brief/`, symlinked into `~/.claude/commands/brief`):
  - `/brief:run [profile]` — full sweep, profile defaults to `general`
  - `/brief:topic <topic> [profile] [sources]` — single-topic research
  - `/brief:setup [profile]` — interactive author/edit (we do NOT invoke this from NSAF; NSAF writes profiles directly)
  - `/brief:status`, `/brief:help`
- **CLI** (`brief …`):
  - `brief init` (one-time)
  - `brief profile list --json`
  - `brief profile show <slug> --json`
  - `brief status --json`
- **Data layout:**
  ```
  $NSAF_BRIEF_HOME/data/
    profiles/<slug>/
      reference.md         # YAML-frontmatter + topics/sources (see assets/profile-template.md)
      history.md
      knowledge-base.md
    briefs/<slug>/<YYYY-MM-DD-HHMM>/
      brief.html
      summary.md
      podcast-script.md    # already produced by /brief:run
      podcast.mp3          # NEW — produced by our NotebookLM post-step
      run.json
      run.log
  ```
- **Profile YAML format:** `assets/profile-template.md` in the Daily-Brief repo — read it for the exact `---` frontmatter + `## Topics` section schema.

### 2.3 NotebookLM skill

Already available as `notebooklm` skill in Claude Code. Activated by explicit intent like "create a podcast about X". For our use: in the same Claude session as `/brief:run`, after the brief completes, invoke NotebookLM with:
- **Source:** `data/briefs/<slug>/<TS>/summary.md`
- **Prompt:** generic — `"5–7 minute two-host explainer podcast covering the brief items in order; warm, conversational tone; assume the listener is busy."`
- **Output:** save returned MP3 to `data/briefs/<slug>/<TS>/podcast.mp3`

Per-profile customization of the podcast prompt is **v2**.

---

## 3. Prerequisites (manual, done once by the user)

Outside the scope of the build agents. Document in `docs/nsaf-dev-guide.md` "External Integrations" table under a new row.

```bash
# On the NSAF server (Tailscale IP)
cd ~ && git clone https://github.com/<user>/Daily-Brief.git
cd Daily-Brief && python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env       # set PERPLEXITY_API_KEY
ln -s "$(pwd)/commands/brief" ~/.claude/commands/brief
brief init                  # creates data/ + general profile

# Then add to ~/nsaf/.env:
NSAF_BRIEF_HOME=/home/smahoney/Daily-Brief

# And confirm Perplexity MCP is in ~/.claude/settings.json
```

The build agents may **assume** `$NSAF_BRIEF_HOME` is populated and the `brief` CLI is on PATH for the user the orchestrator runs as.

---

## 4. Build Order

Six steps. Each ends with a working commit. Stop after **Step 2** and **Step 4** for user smoke-test before proceeding.

| # | Step | Allows |
|---|---|---|
| 1 | Foundation: env + schema + index.js type dispatch | nothing user-visible, unblocks 2 |
| 2 | Spawner + stall + completion | manual DB row → end-to-end run works |
| 3 | `cmd_brief` dispatcher (`run`, `topic`, `profiles`, `status`) | Webex `brief run general` works |
| 4 | NotebookLM chain step + Webex completion attachments | full UX for pre-existing profiles |
| 5 | Q&A `brief setup` + YAML shortcut | profile authoring from Webex |
| 6 | Help text + dev-guide doc update + final polish | shippable |

---

## Step 1 — Foundation

**Goal:** add the `brief` project_type to the data model and orchestrator dispatch. No spawner/completion logic yet — that's Step 2.

### Files

- `.env.example`
- `orchestrator/src/db.js`
- `orchestrator/src/index.js`
- `shared/db.py` (likely no change — `ALLOWED_PROJECT_FIELDS` already covers what we need; verify)

### Changes

**`.env.example`** — add under a new `# --- Daily-Brief integration ---` section:

```
# --- Daily-Brief integration (`brief` Webex commands) ---
# Path on the server to the Daily-Brief install (separate repo).
# All profiles, history, briefs live under $NSAF_BRIEF_HOME/data/.
NSAF_BRIEF_HOME=
```

**`orchestrator/src/db.js`** — add a new table for Q&A state (used in Step 5, declared now so the migration lands early):

```sql
CREATE TABLE IF NOT EXISTS brief_setup_state (
  slug TEXT PRIMARY KEY,
  room_id TEXT NOT NULL,
  step TEXT NOT NULL,                 -- 'role'|'topics'|'sources'|'confirm'|'done'
  answers TEXT NOT NULL DEFAULT '{}', -- JSON blob
  current_topic_idx INTEGER DEFAULT 0,
  started_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

Also expose CRUD helpers (`briefSetupGet`, `briefSetupUpsert`, `briefSetupDelete`, `briefSetupList`) — pattern: read existing vision_* helpers if any, else mirror the pattern from `shared/db.py`'s vision state.

**`orchestrator/src/index.js`** — extend the skip-port-DB branches to include `'brief'`:

```js
// line ~69
if (projectType === 'studyws' || projectType === 'story' || projectType === 'brief') {
  // skip port allocation + per-project Postgres
  ...
}
// line ~108
if (projectType === 'studyws' || projectType === 'story' || projectType === 'brief') {
  // content-pipeline spawn path
  ...
}
```

**`shared/db.py`** — verify `ALLOWED_PROJECT_FIELDS` already contains the fields we need (`slug`, `status`, `project_type`, `project_dir`, `sdd_phase`, `sdd_progress`, `deployed_url`, `last_state_change`, `stall_alerted`, etc.). No new column needed on `projects` for brief — we store profile/topic/run-id in a per-project `brief-config.json` (see Step 3).

### Acceptance

- `node -e "require('./orchestrator/src/db.js').init()"` runs without error and creates `brief_setup_state`.
- Inserting a row `(slug='test', project_type='brief', status='queued', project_dir='/tmp/test')` and enqueueing it does NOT trigger port allocation or per-project Postgres creation on the next orchestrator tick (verify by tailing `/tmp/nsaf-orch.log`).
- No regression in existing studyws/story dequeue paths.

---

## Step 2 — Spawner + stall + completion

**Goal:** when a `brief` project is dequeued, spawn the right Claude session and detect completion.

### Files

- `orchestrator/src/spawner.js`
- `orchestrator/src/stall.js`
- `orchestrator/src/completion.js` (or wherever the type-specific completion check lives — verify by grepping for the studyws completion signal `textbook.md`)

### Per-project config file

Each brief NSAF project's `project_dir` (e.g. `~/nsaf/projects/brief-general-2026-06-29-1830/`) contains a single file written by the Webex command (Step 3):

**`brief-config.json`**
```json
{
  "mode": "run" | "topic",
  "profile": "general",
  "topic": "<optional, only when mode=topic>",
  "started_at": "2026-06-29T18:30:00Z"
}
```

`mode` decides which slash command to invoke. `started_at` is the wall-clock the Webex command fired; the orchestrator uses it to filter brief subdirs newer than this timestamp when watching for completion.

### `spawner.js`

Add a new branch after the existing `story` branch:

```js
} else if (projectType === 'brief') {
  const briefHome = process.env.NSAF_BRIEF_HOME;
  if (!briefHome || !existsSync(briefHome)) {
    log.error({ slug }, 'NSAF_BRIEF_HOME not set or directory missing — cannot spawn brief');
    return null;
  }
  const cfg = JSON.parse(readFileSync(join(dir, 'brief-config.json'), 'utf-8'));
  const profile = cfg.profile || 'general';
  const invocation = cfg.mode === 'topic'
    ? `/brief:topic "${cfg.topic.replace(/"/g, '\\"')}" ${profile}`
    : `/brief:run ${profile}`;

  prompt = `Generate a daily brief autonomously with NO human interaction.
Do NOT ask any questions — proceed with defaults for everything.

Step 1: ${invocation}

Step 2: After the brief completes successfully, locate the newest dated
directory under data/briefs/${profile}/ (the one you just created). Call it RUN_DIR.

Step 3: Use the notebooklm skill to generate a 5-7 minute two-host
explainer podcast from RUN_DIR/summary.md. Tone: warm, conversational;
assume the listener is busy. Save the resulting MP3 as RUN_DIR/podcast.mp3.

Step 4: Verify all three files exist: brief.html, summary.md, podcast.mp3.
Then exit.`;

  cwd = briefHome;
  // Brief sessions need OPENAI_API_KEY (NotebookLM/audio) and PERPLEXITY_API_KEY
  // (research). Keep the same env strip rules as story.
}
```

The env-strip block currently has an `if (projectType !== 'story')` guard (around `spawner.js:308`). **Update it** so brief is also exempt from stripping `OPENAI_API_KEY` and `PERPLEXITY_API_KEY`:

```js
if (projectType !== 'story' && projectType !== 'brief') {
  // existing strip logic
}
```

### `stall.js`

Add a brief branch mirroring studyws (process + output-dir based):

```js
if (projectType === 'brief') {
  const briefHome = process.env.NSAF_BRIEF_HOME;
  const cfg = JSON.parse(readFileSync(join(project.project_dir, 'brief-config.json'), 'utf-8'));
  const runRoot = join(briefHome, 'data', 'briefs', cfg.profile || 'general');
  // Stalled iff: no claude process AND no new run dir newer than cfg.started_at
  const claudeAlive = isClaudeRunningForProject(project.slug);
  const hasNewRun = directoryContainsSubdirNewerThan(runRoot, cfg.started_at);
  if (!claudeAlive && !hasNewRun) return true; // stalled
  return false;
}
```

(`isClaudeRunningForProject` and `directoryContainsSubdirNewerThan` are sketches — reuse studyws helpers if available.)

### `completion.js` / spawner exit handler

After the claude session exits, detect completion by:

1. Find the newest `data/briefs/<profile>/<TS>/` dir with mtime ≥ `cfg.started_at`.
2. Verify it contains `brief.html`, `summary.md`, AND `podcast.mp3`.
3. If yes → `projects.status='deployed-local'`, write the run dir path to `projects.deployed_url` (overload, easiest path) or add a new `brief_run_dir` column if cleaner.
4. If no → leave as-is (stall detection will catch it).

**Recommendation:** add a new column `brief_run_dir TEXT` on `projects` rather than overloading `deployed_url`. The Webex notification path needs to know where to find the files; explicit beats overloaded.

### Acceptance

- Manually insert a row:
  ```sql
  INSERT INTO projects (slug, project_dir, project_type, status)
  VALUES ('brief-general-2026-06-29-1830', '/home/smahoney/nsaf/projects/brief-general-2026-06-29-1830', 'brief', 'queued');
  ```
  After creating `project_dir/` with a valid `brief-config.json` (`{"mode":"run","profile":"general","started_at":"..."}`) and enqueueing it, the orchestrator must:
  - Spawn Claude with `cwd=$NSAF_BRIEF_HOME`
  - The Claude session runs `/brief:run general` then NotebookLM
  - On exit, the orchestrator detects `brief.html` + `summary.md` + `podcast.mp3` in the new run dir
  - Sets `status='deployed-local'` and records the run dir
- A killed Claude session (e.g. `pkill -f 'claude.*brief:run'`) gets flagged as stalled within one stall-detection cycle.

**STOP after this step. Have the user run an end-to-end test before proceeding.**

---

## Step 3 — `cmd_brief` dispatcher

**Goal:** Webex `brief run <profile>` / `brief topic <topic> [--profile <slug>]` / `brief profiles` / `brief status [<slug>]` works. **No setup flow yet** — assume profiles pre-exist on the server.

### Files

- `flask-app/bot/commands.py`

### New function: `cmd_brief(arg, attachments=None)`

Dispatch on first token. Mirror the structure of `cmd_vision` (`commands.py:422`).

```python
def cmd_brief(arg, attachments=None):
    """Daily-Brief: research-driven news catch-up."""
    if not arg:
        return _brief_help()
    parts = arg.strip().split(maxsplit=1)
    sub = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "run":
        return _brief_run(rest)
    if sub == "topic":
        return _brief_topic(rest)
    if sub in ("profiles", "list"):
        return _brief_profiles()
    if sub == "status":
        return _brief_status(rest)
    if sub == "setup":
        return _brief_setup(rest, attachments)   # implemented in Step 5
    if sub == "help":
        return _brief_help()
    return f"Unknown subcommand `{sub}`. Try `brief help`."
```

Register in the handlers dict (around `commands.py:50`):
```python
"brief": cmd_brief,
```

### `_brief_run(rest)`

```python
def _brief_run(rest):
    """Queue a Daily-Brief sweep for a profile."""
    import json as _json
    import re, time
    profile = (rest.strip().split() or ["general"])[0]
    profile = re.sub(r"[^a-z0-9-]+", "-", profile.lower()).strip("-") or "general"

    ts = time.strftime("%Y-%m-%d-%H%M", time.localtime())
    slug = f"brief-{profile}-{ts}"
    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, slug)
    os.makedirs(project_dir, exist_ok=True)

    cfg = {
        "mode": "run",
        "profile": profile,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(os.path.join(project_dir, "brief-config.json"), "w") as f:
        _json.dump(cfg, f, indent=2)

    import sqlite3
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status) VALUES (?, ?, 'brief', 'queued')",
            (slug, project_dir),
        )
        db.commit()
        pid = cursor.lastrowid
    except sqlite3.IntegrityError:
        return f"Project `{slug}` already exists."
    queue_enqueue(pid)
    return (
        f"**Brief queued: `{slug}`**\n"
        f"**Profile:** {profile}\n"
        f"Will research, render, and generate a podcast. Building when a slot opens."
    )
```

### `_brief_topic(rest)`

Parse `topic` (required, free-text) + optional `--profile <slug>` flag (reuse `_extract_flag` already in `commands.py`). Same enqueue pattern; `cfg["mode"]="topic"`, `cfg["topic"]=topic`.

### `_brief_profiles()`

Shell out to the `brief` CLI via the Daily-Brief install:

```python
def _brief_profiles():
    brief_home = os.environ.get("NSAF_BRIEF_HOME", "")
    if not brief_home:
        return "`NSAF_BRIEF_HOME` is not set in `.env`."
    brief_cli = os.path.join(brief_home, ".venv", "bin", "brief")
    if not os.path.isfile(brief_cli):
        brief_cli = "brief"  # fall back to PATH
    try:
        result = subprocess.run(
            [brief_cli, "profile", "list", "--json"],
            cwd=brief_home, capture_output=True, text=True, timeout=10, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return f"`brief profile list` failed: {getattr(e, 'stderr', None) or e}"
    import json as _json
    profs = _json.loads(result.stdout)
    if not profs:
        return "No profiles yet. Run `brief setup <slug>` to create one."
    lines = ["**Daily-Brief profiles:**"]
    for p in profs:
        lines.append(f"- `{p['slug']}` — {p['title']}")
    return "\n".join(lines)
```

### `_brief_status(rest)`

If `rest` is empty: shell out `brief status --json`, format as a Webex-friendly summary.
If `rest` is a slug: `brief profile show <slug> --json`, print title + description + topics count + history count + last-run timestamp.

### `_brief_help()`

```
**Daily-Brief commands**
- `brief run [profile]` — full sweep, default profile `general`
- `brief topic <topic> [--profile <slug>]` — single-topic research
- `brief setup <slug>` — guided profile creation (or paste a fenced YAML body in the same message)
- `brief profiles` — list profiles
- `brief status [<slug>]` — overall or per-profile status
- `brief help` — this message
```

### Acceptance

- `brief help` → returns the help text
- `brief profiles` → lists `general` (after manual `brief init` on server)
- `brief run general` → creates a row, enqueues, message says queued
- The row makes it through the orchestrator (Step 2) end-to-end
- `brief status` → shows the profile

---

## Step 4 — NotebookLM chain + Webex completion attachments

**Goal:** when a brief completes, post a Webex message attaching `brief.html`, `summary.md`, AND `podcast.mp3`.

### Files

- `orchestrator/src/notify.js` (or wherever per-type completion notifications live; grep for the studyws completion notification first)
- Possibly `bot/notifications.py` if attachments are sent from Flask

### Investigation phase (do first)

```bash
grep -nE "completion|deployed-local|notify" orchestrator/src/notify.js orchestrator/src/completion.js 2>/dev/null
grep -nE "files=|file_attach|attachments" flask-app/bot/notifications.py orchestrator/src/notify.js
```

Confirm how a completion notification is posted today for studyws/story (it's a Webex card with a link). For brief we need **actual file attachments**. Webex Bot API supports multipart upload via the `files` form field on `POST /messages` — single file per message; for three files we either:
- (a) Send one message with the brief.html attached + a card linking to the rest (cleanest if attachments are limited to 1)
- (b) Send three messages back-to-back, one per file
- (c) Bundle into a single ZIP and attach that

**Recommendation:** (b) — three messages. The first message has the headline + brief.html, the second has summary.md, the third has podcast.mp3. Clear, no zipping, easy to download each.

### Implementation

In the orchestrator completion path for `project_type='brief'`:

1. Read `brief_run_dir` from the projects row (set in Step 2).
2. Post 3 Webex messages (use existing `notify.js` helper, extending it to accept a `files` array if it doesn't already):
   - `**Brief ready: <slug>**  N items (M new). Profile: <profile>.` + attach `brief.html`
   - `Summary markdown:` + attach `summary.md`
   - `Podcast (5–7 min, NotebookLM):` + attach `podcast.mp3`
3. Mark project completed (already done by Step 2).

### Acceptance

- After a successful `brief run general` end-to-end (Steps 1–4), the Webex room receives 3 messages with the 3 files attached and downloadable in the Webex client.
- File sizes: brief.html (<200 KB), summary.md (<50 KB), podcast.mp3 (5–25 MB). All well under Webex's 100 MB per-attachment cap.

**STOP after this step. Have the user smoke-test the full happy path before tackling setup.**

---

## Step 5 — Q&A `brief setup` + YAML shortcut

**Goal:** authoring a profile from Webex without SSH. Mirror the `vision` Q&A pattern.

### Files

- `flask-app/bot/commands.py` — add `_brief_setup(...)` and helpers
- (Optional) `flask-app/bot/brief_setup.py` — extract the Q&A engine if it grows past ~200 lines, matching `flask-app/bot/vision.py`

### YAML shortcut (do first — easier)

If the user's `brief setup <slug>` message contains a fenced YAML block in the body (e.g. ` ```yaml ... ``` ` or ` ```markdown\n---\n... ``` ` with the profile frontmatter format), bypass Q&A entirely:

1. Validate slug is `[a-z0-9-]+`
2. Parse the YAML body (top-level frontmatter + topics list — see `assets/profile-template.md` for the exact schema)
3. Validate it parses by writing it to a tmp file and running `brief profile show <slug>-tmp --json` (or do a Python-side pydantic validation if the daily_brief package is importable from the venv — easier and faster)
4. Write to `$NSAF_BRIEF_HOME/data/profiles/<slug>/reference.md` (create `history.md` + `knowledge-base.md` as empty files alongside)
5. Reply with summary: "Created profile `<slug>` — N topics, M sources. Run `brief run <slug>` to test."

### Multi-turn Q&A

State machine in `brief_setup_state`. One row per in-progress slug.

Steps (`step` column values):
1. **role** — bot asks: "What role/lens is this profile for? (e.g. 'an AI engineer who runs a startup'). This frames every 'why this matters'."
2. **title** — bot asks: "Display name? (e.g. 'AI Engineer')"
3. **topics** — bot asks: "What topics? (one per line, e.g. 'Anthropic releases', 'LLM cost trends'). Reply with a numbered or bulleted list."
4. **sources** — for each topic, bot asks: "Sources for `<topic>`? Format: `<Name> (<type>) <optional URL>` one per line. Types: website, blog, news, web-search, youtube. Reply `web-only` to use only open-web research, or `skip` for no specific sources (still uses web search)."
   - `current_topic_idx` in the row tracks which topic we're on.
5. **confirm** — bot renders the would-be `reference.md` and asks "Looks right? Reply `yes` to write or `cancel` to abort."
6. **done** — write the file, delete the state row, reply with success.

The state machine reads each follow-up message in the same Webex room with no command prefix (i.e. the bot intercepts the next user message after `brief setup <slug>` if a row exists for that room). Pattern: look at how `vision` intercepts follow-ups in `flask-app/routes/webex.py` and `bot/vision.py`.

### Acceptance

- `brief setup ai-eng` with fenced YAML body → profile created on disk
- `brief setup ai-eng` without body → bot asks the role question, accepts replies, eventually writes reference.md
- `brief profiles` after either path shows the new profile
- `brief run ai-eng` works against the freshly created profile
- `brief setup ai-eng cancel` (anywhere in the flow) deletes the state row and tells the user

---

## Step 6 — Help, dev-guide, polish

### Files

- `flask-app/bot/commands.py` — `cmd_help()` (bottom of file) — add the `brief` section
- `docs/nsaf-dev-guide.md` — add the `Daily-Brief` row under "External Integrations" table; add a "Daily-Brief" row to the Project Types table; document the manual install in "Prerequisites"
- `README.md` — add `brief` to the Webex bot commands section if there is one

### Acceptance

- `help` in Webex shows the brief commands
- `docs/nsaf-dev-guide.md` documents the install + integration
- No lint/syntax errors (`python3 -c "import ast; ast.parse(open('flask-app/bot/commands.py').read())"`)
- Server restart instructions documented (Flask pickup `brief` commands; orchestrator pickup spawner/stall changes)

---

## 5. Testing each step

| Step | Smoke test |
|---|---|
| 1 | Manual sqlite insert + `node -e require('./db.js').init()` |
| 2 | Manual row + `brief-config.json` → tail `/tmp/nsaf-orch.log`, watch run dir |
| 3 | Webex: `brief help`, `brief profiles`, `brief run general` (will queue but spawn will work because Step 2 is done) |
| 4 | Webex: full `brief run general` round-trip, expect 3 attachments in the room |
| 5 | Webex: `brief setup test-profile` Q&A + YAML body variant |
| 6 | Read `help`, read the updated dev-guide |

---

## 6. Server-side restart sequence after each push

```bash
# After Steps 1, 2: orchestrator code changed
ssh $NSAF_SERVER "cd $NSAF_HOME && git pull && pkill -f 'node orchestrator/src/index.js'; sleep 2 && nohup node orchestrator/src/index.js > /tmp/nsaf-orch.log 2>&1 < /dev/null & disown"

# After Steps 3, 4, 5, 6: Flask code changed
ssh $NSAF_SERVER "cd $NSAF_HOME && git pull && pkill -f 'flask-app/app.py'; pkill -f ngrok; sleep 3 && nohup venv/bin/python flask-app/app.py > /tmp/nsaf-flask.log 2>&1 < /dev/null & disown"
```

---

## 7. Non-goals (do not implement)

- Promotion to website (`promote brief`)
- In-app scheduling (cron-style triggers)
- Per-profile podcast prompts (generic prompt only for v1)
- YouTube source ingestion (Daily-Brief itself defers this)
- Knowledge-base querying (write-only in v1; Daily-Brief defers querying to v2)
- Editing existing profiles from Webex (v1 = create only; edits via SSH)
- Multi-user / per-Webex-user profile namespacing (single-tenant)

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| NotebookLM skill rate limits or quota | Treat audio generation as best-effort: if it fails, complete the project with brief.html + summary.md only, post 2 attachments instead of 3, log the audio failure. Implement in Step 4. |
| Profile YAML in Webex gets mangled by message formatting | YAML shortcut REQUIRES a fenced ```yaml or ```markdown code block; reject (with a clear error) anything else. |
| Long-running `/brief:run` exceeds 5-min default timeout | The orchestrator already has no fixed timeout for content pipelines (it watches for completion via state). Verify by reading the spawner default in spawner.js — no timeout argument means it waits until the Claude process exits. |
| Webex attachment size limit | 100 MB is the per-attachment cap; podcast.mp3 at 24 kbps stereo for 7 min ≈ 1.3 MB, at 192 kbps stereo ≈ 10 MB. Well within limits. |
| `$NSAF_BRIEF_HOME` not configured | Spawner returns early with a clear log line; cmd_brief subcommands fail-fast with "set NSAF_BRIEF_HOME in .env". Implement in Steps 2 and 3. |
