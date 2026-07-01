---
description: Scope a variant=explainer techguide — single-page concept explainer
---

# /tg:scope-explainer — Outline a single-page concept explainer

You were dispatched here from `/tg:scope` because `variant=explainer`.

An **explainer** techguide is a single-page deep explanation of ONE concept.
Think: "What is SD-WAN?" — a focused page a curious engineer can read end-to-end
in 10–20 minutes, dense with diagrams, no chaptering, no navigation tabs.
Output is one HTML file at `output/<slug>/guide/index.html`.

## Your job

Produce `output/<topic-slug>/outline.json` with the following shape:

```json
{
  "topic": "<from config.topic>",
  "variant": "explainer",
  "level": "<from config.level>",
  "thesis": "1–2 sentence statement of what the explainer claims — the answer to the implied question in the topic.",
  "concept_blocks": [
    {
      "id": "block-01",
      "slug": "what-is-it",
      "title": "What it is",
      "summary": "1–2 sentence summary of this block's role in the page.",
      "key_ideas": ["idea A", "idea B", "idea C"],
      "diagram_hint": "1 sentence describing the visual/diagram this block should anchor on (the build stage will produce the actual SVG)",
      "approximate_word_count": 400
    },
    ...
  ],
  "takeaways": [
    "1 sentence: a single concrete claim the reader should walk away with.",
    "1 sentence: another.",
    "..."
  ]
}
```

## Block rules

- **3–5 concept blocks.** Fewer means the topic is too thin for an explainer
  (consider whether it should be a vision note instead). More means it's a
  deep guide, not an explainer.
- **Each block is a single idea.** Examples for "What is SD-WAN?":
  1. What it is (definition + 1-line mental model)
  2. The problem it solves (vs. legacy WAN)
  3. How it works (the technical core — overlay, tunnels, controller)
  4. What it doesn't do (the boundary — security, SaaS optimization)
  5. When to pick it (the decision frame)
- **`diagram_hint` is required** — an explainer is SVG-heavy. Each block should
  anchor on one visual idea the diagrams stage will render.
- **`approximate_word_count`** total across blocks should be 1500–3000 words —
  meaningful but reader-completable in one sitting.

## Takeaways

3–5 single-sentence claims. These appear as a numbered list at the end of the page.
They are NOT a summary — they are the operational answers a reader carries away.

## Source-material handling

If `has_source_file: true` (e.g. an RFC, vendor whitepaper, blog post), the file
is the source. The thesis should reflect what the source actually argues, not
the explainer-writer's own opinion.

If `source_url` is set, fetch it via WebFetch and treat similarly.

## Forbidden

- No `chapters`, `sections`, or `products` arrays — these are `concept_blocks`.
- No multi-page navigation hints — this is ONE page.
- No FAQs (`takeaways` covers the equivalent role).
- No quizzes.

## When done

Save `outline.json`, then return control to the parent dispatcher.
The dispatcher will auto-chain to `/tg:research`.
