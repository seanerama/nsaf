---
description: Render variant=explainer — single rich SVG-heavy page
---

# /tg:build-explainer — Render the single-page explainer

You were dispatched here from `/tg:build` because `variant=explainer`.

## Output layout

```
output/<topic-slug>/guide/
└── index.html              # ONE FILE — the entire explainer
```

An explainer is a single rich page. The promote step ships this as
`public/guides/<slug>.html` (single-page form).

## Page structure

```
┌──────────────────────────────────────────────────────┐
│  TITLE                                               │
│  (outline.topic)                                     │
├──────────────────────────────────────────────────────┤
│  THESIS                                              │
│  - render outline.thesis as a callout block,         │
│    typographically distinct from body copy           │
│    (larger font, --color-primary-light background,   │
│    left border accent in --color-primary)            │
├──────────────────────────────────────────────────────┤
│  CONCEPT BLOCKS — one <section> per outline.concept_blocks[] │
│  - title (h2), 400-word development                  │
│  - inline SVG diagram (NOT external image file)      │
│    sourced from output/<slug>/diagrams/block-NN.svg  │
├──────────────────────────────────────────────────────┤
│  TAKEAWAYS                                           │
│  - render outline.takeaways[] as a numbered list,    │
│    visually distinct (--color-surface card)          │
├──────────────────────────────────────────────────────┤
│  REFERENCES                                          │
│  - footnote-style citations from explainer.md        │
└──────────────────────────────────────────────────────┘
```

## Concept block rendering

For each `concept_block` in outline order:

```html
<section id="<block.slug>" class="concept-block">
  <h2>{block.title}</h2>

  <div class="block-body">
    {render the matching block content from explainer.md}
  </div>

  <figure class="block-diagram">
    {inline SVG read from output/<slug>/diagrams/block-NN.svg}
    <figcaption>{block.diagram_hint}</figcaption>
  </figure>
</section>
```

## Diagrams — SVG-heavy is the point

This variant is SVG-heavy. Inline EVERY diagram as a literal `<svg>` tag in
the HTML — no `<img src="...">`, no Mermaid CDN render.

If `/tg:diagrams` produced Mermaid sources (`.mmd`) rather than SVG, render
them server-side via Mermaid CLI (`@mermaid-js/mermaid-cli`) if available,
OR fall back to including the Mermaid runtime script and a `<pre class="mermaid">`
block. SVG-first is preferred.

## Layout standards

- Max body width 760px centered.
- Generous vertical rhythm — explainer is the most "designed" variant.
  Each concept block separated by ~60-80px vertical space, the diagram is
  centered with full-width room (up to 720px).
- Thesis callout uses `--color-primary` accent on a `--color-primary-light`
  background, with a left-border `border-left: 4px solid --color-primary`.
- Takeaways block uses a `--color-surface` card with a slight box-shadow.

## File-naming rule

- Single file at `output/<slug>/guide/index.html`.
- This single-file shape is what `/tg:promote` detects as the explainer/comparison
  layout — it ships the page as `public/guides/<slug>.html`.

## Forbidden

- No multi-page split.
- No table of contents (the page is short enough to scroll; TOC adds visual noise).
- No external image files. EVERY diagram is inline `<svg>`.
- No external CSS/JS files. Inline `<style>` and `<script>` only.
- No `<div class="sws-quiz">…` blocks.

## When index.html is written

The dispatcher decides whether to auto-chain to `/tg:promote` or stop.
