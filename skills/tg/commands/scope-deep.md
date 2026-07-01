---
description: Scope a variant=deep techguide — multi-section deep-dive outline
---

# /tg:scope-deep — Outline a multi-section deep-dive guide

You were dispatched here from `/tg:scope` because `variant=deep`.

A **deep** techguide is a multi-section interactive HTML guide on one topic.
Think: a comprehensive long-form web reference, ~5–12 sections, each ~600–1200
words of content, with inline SVG/Mermaid diagrams. The reader navigates
section-by-section via a hub-and-spoke layout.

## Your job

Produce `output/<topic-slug>/outline.json` with the following shape:

```json
{
  "topic": "<from config.topic>",
  "variant": "deep",
  "level": "<from config.level>",
  "sections": [
    {
      "id": "section-01",
      "slug": "what-is-x",
      "title": "What is X?",
      "summary": "1–2 sentence summary of what this section covers and why it appears here.",
      "key_topics": ["concept A", "concept B", "concept C"],
      "approximate_word_count": 800
    },
    ...
  ]
}
```

## Sectioning rules

- **5–12 sections.** Choose the number based on topic breadth — don't pad. For a
  narrow topic (one product, one protocol), 5–7 sections. For a broad topic
  (a whole platform, a discipline), 9–12. Never fewer than 5 or more than 12.
- **Each section is a self-contained concept the reader could navigate to directly.**
  Sections should NOT be sub-steps of one procedure — they should be standalone
  topics that build on each other when read in order, but stand alone if jumped to.
- **Order matters but isn't strictly linear.** Earlier sections cover prerequisites
  and concepts; later sections cover advanced/specialized material.
- **`slug` is URL-safe** — lowercase, hyphenated, no special chars. Used in the
  HTML filename later (`section-NN-<slug>.html`).
- **`approximate_word_count`** is a target for the write stage (600–1200 typical;
  intro/conclusion sections can be 400–500).

## Source-material handling

If `has_source_file: true` in config, the file at `source-material.md`
(or `.pdf`) is the **primary source**. Derive section topics and order from
its structure. Do not invent sections the source doesn't support; do not
omit substantive material the source covers.

If `source_url` is set, fetch it via WebFetch and treat it the same way.

## Forbidden

- No `chapters` array — these are `sections`.
- No textbook companion (`textbook.md`).
- No quiz blocks.
- No outlining the eventual HTML — that's the build stage's job.

## When done

Save `outline.json`, then return control to the parent dispatcher.
The dispatcher will auto-chain to `/tg:research`.
