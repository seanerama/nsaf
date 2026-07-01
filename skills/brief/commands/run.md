---
description: Sweep a profile's subscribed sources for the latest and produce a brief
---

# /brief:run [profile]

Run a full Daily-Brief sweep for a profile: research its topics across their predetermined
sources (Claude sub-agents) and the open web (Perplexity), dedup against history, frame each
item through the profile lens, and emit the interactive HTML + markdown summary + podcast script.

Profile defaults to `general` if not given in `$ARGUMENTS`.

The `brief` CLI does ALL deterministic work; the AI work is done by **sub-agents** and the
**Perplexity MCP**. Sub-agents return **structured JSON only** (except the podcast script).
See `sdd-output/contracts/subagent-contracts.md`.

## Process

1. **Resolve the profile.** Run `brief profile show <slug> --json`. If it errors, tell the user
   to `/brief:setup <slug>` first. Generate a timestamp `TS` = current local time as `YYYY-MM-DD-HHMM`.

2. **Fan out research sub-agents — one per topic, in parallel** (single message, multiple
   Agent tool calls). For each topic:
   - If the topic has predetermined `sources`: spawn a **Claude research sub-agent** that uses
     WebFetch/WebSearch to check those sources for the latest items on the topic. It must return
     a `ResearchResult` JSON (subagent-contracts §1) with `source.type` = the source's type.
   - If `web_search: true`: also do **Perplexity research** via the Perplexity MCP (Sonar Pro)
     for the latest on the topic; shape the result as a `ResearchResult` with
     `source = {name:"Perplexity", type:"web-search"}`.
   - Each sub-agent captures per-source problems in `failures` and never aborts the whole run.

3. **Collect + flatten** all `ResearchResult.items` into one JSON list; collect all `failures`.
   Write items to a temp file (e.g. `data/briefs/<slug>/<TS>/_raw-items.json`).

4. **Dedup:** `brief dedup <slug> --items-file _raw-items.json --mode annotate` → deduped items
   (ids assigned, prior coverage annotated). Save to `_deduped.json`.

5. **Frame:** spawn ONE **framing sub-agent** (subagent-contracts §2) given the deduped items +
   the profile `description`. It returns `{items:[{id, why_it_matters}]}`. Merge `why_it_matters`
   back onto the deduped items by `id` → `_items.json`.

6. **Assemble + render:**
   - `brief assemble <slug> <TS> --trigger run --started-at <ISO> --items-file _items.json --failures-file _failures.json`
   - `brief render <slug> <TS>`  (writes brief.html + summary.md from run.json)

7. **Podcast script:** `brief podcast-prompt <slug> <TS>` → pass that prompt to a **podcast
   sub-agent** (subagent-contracts §3) → write its markdown output to
   `data/briefs/<slug>/<TS>/podcast-script.md`.

8. **Persist:**
   - `brief history-from-run <slug> <TS>` (append history).
   - Optionally distill 1–5 durable learnings and `brief kb-append <slug> --json-file` with
     `{"date":"<YYYY-MM-DD>","learnings":[...]}`.
   - Write a short human `run.log` into the run dir noting what was checked and any failures.

9. **Report** to the user: the run dir path, item counts (new vs prior), any failures, and a
   one-line teaser. Offer to open `brief.html`.

## Rules
- Clean up the `_raw-items.json` / `_deduped.json` / `_items.json` / `_failures.json` temp files
  when done (the persistent artifacts are brief.html, summary.md, podcast-script.md, run.json, run.log).
- Never invent facts; if a source can't be reached, record a failure and move on.
