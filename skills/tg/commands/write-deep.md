---
description: Write content for variant=deep — one .md per section, in parallel
---

# /tg:write-deep — Author the section markdowns

You were dispatched here from `/tg:write` because `variant=deep`.

## Your job

For each entry in `outline.json.sections[]`, produce one markdown file at:

```
output/<topic-slug>/sections/section-NN-<slug>.md
```

where `NN` is the 1-indexed position in the array (`01`, `02`, …) and `<slug>`
is the section's `slug` from outline.json.

## Parallelism

Spawn parallel sub-agents via the Agent tool — one per section. Each sub-agent
receives ONE outline entry + ONE research file (from `research/<matching>.md`).
Wait for all to complete before returning.

## Each section file

Frontmatter:
```yaml
---
section_id: section-NN
title: "..."           # from outline.json
slug: "..."            # from outline.json
order: NN              # integer
---
```

Body:
- **First paragraph**: 1–2 sentences answering "what does this section cover, and
  why is it here?" — orients a reader who landed here from search.
- **2–5 H2 (`##`) subsections** that develop the section's key_topics.
- **Inline code blocks** for commands, configs, schemas. Use ` ``` ` fences with
  a language tag (`bash`, `yaml`, `json`, etc.).
- **Citations** as footnote-style references at the bottom of the file under
  a `## References` H2 — link to authoritative sources from the research file.
- **Diagram placeholders**: insert `<!-- DIAGRAM: 1-sentence description -->`
  HTML comments where a diagram would help. The diagrams stage replaces these
  with actual SVG/Mermaid.
- **Approximate word count**: target the outline's `approximate_word_count`
  (typical: 600–1200). Don't pad to hit it; don't truncate to dodge it.

## Tone

Technical, precise, opinion when grounded in tradeoffs. Show why decisions
matter for a working engineer. Avoid filler ("In today's fast-paced…"), avoid
hedging ("It is generally believed that…"), avoid first-person voice.

## Source-material discipline

If `has_source_file: true`, the source is authoritative. When the source and
the research material disagree, prefer the source and note the disagreement
in a parenthetical or footnote.

## Forbidden

- No FAQ / Q&A sections (low signal in this format).
- No quiz blocks.
- No `## Summary` or `## Conclusion` sub-sections — the section's last paragraph
  is implicitly the close.
- Do not write into `chapters/` (SWS legacy).

## When all sections are written

Return control to the parent dispatcher. It auto-chains to `/tg:diagrams`.
