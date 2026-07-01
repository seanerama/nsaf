---
description: Research a single topic through a profile lens and produce a brief
---

# /brief:topic <topic> [profile] [sources]

Research ONE topic and produce a brief. `topic` is required. `profile` defaults to `general`.
`sources` is optional — if omitted, use the profile's predetermined sources for that topic (and
open-web search); if given, use those specific sources.

Same engine and contracts as `/brief:run` — the only difference is scope (one topic) and that
history is used to surface *what's new since* the last look at this topic.

## Process

1. **Parse `$ARGUMENTS`** into `topic` (required), `profile` (default `general`), and optional
   `sources`. Run `brief profile show <profile> --json`. Generate timestamp `TS` = `YYYY-MM-DD-HHMM`.

2. **Check prior coverage of this topic:** read `data/profiles/<profile>/history.md` (or
   `brief` history) to see what's already been logged for this topic, so research can focus on
   *what's new since*.

3. **Research the topic** (fan out sub-agents in parallel):
   - Open web via **Perplexity MCP** (Sonar Pro) → `ResearchResult` (source = Perplexity / web-search).
   - If `sources` were given OR the profile topic has predetermined sources: a **Claude research
     sub-agent** over those sources via WebFetch/WebSearch → `ResearchResult`.
   - Capture per-source `failures`; never abort the whole run.

4. **Dedup → frame → assemble → render → podcast → persist** exactly as `/brief:run` steps 3–8,
   but pass `--trigger topic --requested-topic "<topic>"` to `brief assemble`.

5. **Report**: run dir path, what's new vs already-seen, failures, teaser. Offer to open brief.html.

## Rules
- Structured JSON only from research/framing sub-agents; the podcast sub-agent returns markdown.
- Clean up temp `_*.json` files; keep brief.html, summary.md, podcast-script.md, run.json, run.log.
- Never invent facts; record unreachable sources as failures.
