---
description: Write content for variant=explainer — single explainer.md, all blocks inline
---

# /tg:write-explainer — Author the single explainer.md

You were dispatched here from `/tg:write` because `variant=explainer`.

## Your job

Produce ONE file:

```
output/<topic-slug>/explainer.md
```

containing the full single-page explainer. All `concept_blocks` from
`outline.json` are inline in this one file. There are NO separate per-block
files — the final HTML is also one page, so the markdown is one page too.

## Structure

```markdown
---
topic: "<from outline.topic>"
variant: explainer
thesis: "<from outline.thesis>"
---

# <topic>

> **Thesis**: <outline.thesis>

<!-- Concept block 1 — use the title from outline.concept_blocks[0].title -->

## <block 1 title>

<450-word development of the block. Hit each key_idea from
outline.concept_blocks[0].key_ideas. Insert a diagram placeholder where the
diagram_hint applies:>

<!-- DIAGRAM: <block 1 diagram_hint verbatim> -->

<!-- Concept block 2 -->

## <block 2 title>

<450-word development. Diagram placeholder.>

<!-- DIAGRAM: <block 2 diagram_hint verbatim> -->

<!-- ... one ## per concept_block ... -->

## Takeaways

1. <takeaway 1 from outline>
2. <takeaway 2>
3. <takeaway 3>
...

## References

<footnote-style citations gathered from research/explainer.md, deduplicated>
```

## Parallelism

You CAN spawn parallel sub-agents — one per concept block — and assemble their
output. But since this is a single file with a coherent voice, prefer doing
this serially in ONE sub-agent unless the topic is very long. If you do
parallelize, the final assembly must reconcile voice and remove duplicate
"as we saw earlier" cross-references.

## Length

Total: **1500–3000 words**. A reader should finish in 10–20 minutes.

- Less than 1500 → the topic was too thin; you didn't develop the key_ideas.
- More than 3000 → consider whether this should have been `variant=deep`.

## Diagram density

This is the SVG-heavy variant — every concept block gets a
`<!-- DIAGRAM: ... -->` placeholder. The diagrams stage will produce inline
SVGs or Mermaid for each.

For an explainer, prefer **conceptual diagrams** (flow, hierarchy, mental
model) over **dense technical schematics**. The point is to make the abstract
concrete.

## Tone

Direct, opinionated where grounded. The thesis is the answer; the page is
the support. Don't dilute the thesis with hedges. Don't trail off with
"and many other considerations."

## Forbidden

- No multi-page navigation.
- No `chapter-NN.md` or `section-NN.md` files (SWS legacy / wrong variant).
- No quizzes.
- No "Want to learn more?" CTAs to a hypothetical follow-up guide.

## When the file is written

Return control to the parent dispatcher. It auto-chains to `/tg:diagrams`.
