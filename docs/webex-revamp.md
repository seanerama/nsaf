# Webex Bot Revamp: Dispatcher → Relay

**Status:** design doc, not implemented. Prerequisite for any further Webex feature work.

## Motivation

`flask-app/bot/commands.py` currently has **30 `cmd_*` functions** spanning ~3,000 lines. Every new NSAF capability has meant adding another dispatcher: `cmd_sws`, `cmd_story`, `cmd_brief`, `cmd_vision`, `cmd_storyfix`, etc. The bot is now a second surface for describing what NSAF can do — one that has to be kept in sync with the actual skills.

Meanwhile, all the interesting creative capability is now discoverable via `/story:*`, `/sws:*`, `/verity:*`, etc. (skills monorepo in `nsaf/skills/`, commit `10fc174`). Claude Code, running on the server, already knows how to route those. The bot doesn't need to.

**Goal:** the bot stops being a command router. It becomes a transport between Webex and a Claude Code session that IS the router.

## The split: what stays dispatcher-native vs. what goes to relay

Not everything should relay. Some commands are cheap deterministic DB reads that benefit from staying native to the bot process. Others are creative multi-step flows that Claude already handles better than any hardcoded dispatcher.

### Stay native (dispatcher, direct DB / orchestrator control)

These are cheap, deterministic, and touch NSAF's own state:

- `cmd_status` — build queue snapshot from SQLite
- `cmd_start`, `cmd_stop`, `cmd_stopall`, `cmd_pause`, `cmd_pauseall` — orchestrator lifecycle
- `cmd_delete`, `cmd_rebuild`, `cmd_archive`, `cmd_demote`, `cmd_gitpush` — project-record ops
- `cmd_debug`, `cmd_system`, `cmd_tokens`, `cmd_export` — introspection
- `cmd_ideas`, `cmd_stories`, `cmd_studies`, `cmd_idea_detail` — list queries against the ideas DB
- `cmd_queue_idea` — enqueue an app build

These are ~15 of the current 30. They stay as-is (or get a light cleanup pass).

### Relay to Claude (dispatcher goes away)

These are the creative / multi-step flows currently duplicating skill functionality:

- `cmd_sws` → `/sws:start …` in Claude
- `cmd_story`, `cmd_fetchstory`, `cmd_storyfix` → `/story:*`
- `cmd_brief` → `/brief:*` (once brief is skillified — currently lives in flask-app)
- `cmd_vision`, `cmd_idea`, `cmd_idea_brainstorm`, `cmd_modify`, `cmd_generate` → free-form conversation with Claude, which decides the right skill
- Any future `cmd_<new-feature>` — never added again; Claude picks up new skills automatically

These are ~15 of the current 30. They collapse into one relay path.

## What stays in the bot codebase either way

- Webex webhook auth (signature verification, bot token)
- Incoming message handling (webhook → parse envelope → route)
- File attachment handling (download → forward)
- Outgoing message chunking + send (Webex's message length cap)
- ngrok tunnel + webhook config
- Native command dispatch (the 15 that stay)

The dispatcher pattern isn't going away entirely — it's shrinking to just the deterministic ops. Everything else becomes:

```python
# pseudo, in the bot's message handler
if message.text.startswith('!') and first_word in NATIVE_COMMANDS:
    return dispatch_native(first_word, args, attachments)
else:
    return relay_to_claude(user_id, message.text, attachments)
```

## What needs to be built

### 1. Claude Code session manager

Options for session model:

- **Per-user persistent session.** One long-running Claude Code session per Webex user, kept warm. Preserves conversation context across messages. Costs a small amount of ongoing cache maintenance per user; for personal use (1–3 users) this is negligible.
- **Per-user resumable session.** One session per user, but serialized to disk between messages (transcript file), re-hydrated on the next message. Free between messages, small warmup cost per turn.
- **Ephemeral per-message.** No context between messages. Simplest to build, worst UX for iterative work ("wait, no, redo scene 3 with a different tone" no longer works).

**Recommend: per-user resumable.** Uses Claude Code's existing session-resume mechanic. Balance of context preservation and idle cost.

### 2. Relay path

Incoming Webex message → append as user turn to Claude session → stream response → chunk to Webex message length → send. Design constraints:

- **Chunk boundaries must not cut mid-code-block.** Webex renders markdown; a code fence cut across a chunk boundary renders as broken markdown. Chunker must respect fence pairs.
- **Streaming vs buffer.** Buffer-and-send is simpler; streaming (edit-in-place with progressive updates) is nicer UX but Webex doesn't support message edits reliably. Start with buffer-and-send.
- **File attachments:** on the way in, download and inject as filesystem paths in the session's cwd (`~/nsaf/webex-uploads/<user>/<timestamp>-<name>`). Claude then reads them naturally. On the way out, if Claude writes files the user should see, detect via a convention (a specific output dir) and post them back.

### 3. Session persistence

- Session ID mapped to Webex user ID in SQLite (new table: `webex_sessions(webex_user_id, claude_session_id, last_message_at)`).
- Transcript on disk (Claude Code already does this at `~/.claude/projects/…`).
- On restart of Flask: sessions are automatically re-resumable via ID; no separate persistence needed.

### 4. Auth / isolation

- Session cwd is per-user: `~/nsaf/webex-workspaces/<webex_user_id>/`. Prevents users from clobbering each other's project state.
- API keys live in the server's env (Claude subscription, OpenAI, ElevenLabs, gh token). Not per-user.
- If more than one user is expected: consider a shared read model (some skills like `/story:status` should be callable across users' workspaces).

## Open questions

1. **When Claude wants clarification, how does the user answer?** Claude asks a question mid-multi-step-workflow, user replies in Webex, relay passes reply as the next user turn. The session preserves state. This just works IF the session is persistent (per-user resumable model above).
2. **How does the user know Claude is "thinking"?** Long-running skills (story pipeline, sws build) take minutes. Webex needs a heartbeat message ("still working on scene 4 of 10…"). Options: periodic status pings from a monitoring thread, or Claude explicitly writes progress lines that the relay forwards as they stream.
3. **What if Claude picks the wrong skill?** No dispatcher = no keyword safety net. If the user types "make me a story about a bear," Claude has to pick `/story:*` correctly. This is high-probability but not certain. Mitigation: users can still type `/story:start` explicitly and it works — the relay just forwards, and Claude honors slash commands.
4. **Notifications** — currently `flask-app/bot/notifications.py` posts completion pings to Webex when a build finishes. In the relay model, does the completion signal come from Claude ("I'm done") or from the orchestrator (existing path)? Recommend: keep orchestrator-driven notifications; they're independent of the relay.
5. **Cost accounting** — long-running Claude sessions on the subscription still consume the same monthly quota. Per-user session model means a runaway user could burn shared quota. Mitigation: a per-user daily rate limit on the relay (e.g. cap messages/day and forward with backoff).

## Migration plan

Do NOT big-bang this. The dispatchers work today; the relay is a rebuild.

1. **Feature flag.** Add `WEBEX_RELAY_MODE=false` in `.env`. When false: existing behavior. When true: everything not in `NATIVE_COMMANDS` goes through the relay. Ship this behind the flag first.
2. **Build the session manager.** New module `flask-app/bot/relay.py` with the per-user resumable-session model. Test standalone (no Webex integration) via a CLI harness.
3. **Wire the relay path.** In `commands.py`, add the "not in NATIVE_COMMANDS → relay" branch, gated on the feature flag.
4. **Test with yourself.** Turn on the flag, send `hey`, verify Claude responds. Then try `/story:start` explicitly. Then try "build me a story about pandas" (natural language).
5. **Migrate one workflow.** `cmd_sws` is a good candidate — well-understood, has a working skill (`/sws:start`). Delete `cmd_sws`, verify natural-language sws requests work via relay.
6. **Delete dispatchers in batches.** Move to relay one command family at a time. Update the README's Webex section after each batch to keep docs accurate.
7. **Flip the default.** Once all 15 relay-target commands are gone, set the default to `WEBEX_RELAY_MODE=true` and remove the flag.

## Impact on future skill development

The goal state: adding a new skill (new prefix, new command, new subagent) is a **zero-touch** event for the bot. Modify `nsaf/skills/<new-prefix>/`, commit, deploy. Webex users can invoke it immediately by name or by describing what they want. No `cmd_*` function ever again.

That is what "kill divergence, make the skill the source of truth" actually looks like from the user's phone.

## Related

- Skill monorepo layout: `nsaf/skills/`, commit `10fc174`, memory [[nsaf-skill-layout]]
- Dev server: memory [[nsaf-dev-server]] (Flask, orchestrator, idea-generator run under `nohup`)
- Prior brief-integration work (5 commits before `10fc174`) — the dispatcher pattern being retired
