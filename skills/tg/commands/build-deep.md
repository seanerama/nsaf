---
description: Render variant=deep — hub index.html + per-section pages
---

# /tg:build-deep — Render the multi-page hub layout

You were dispatched here from `/tg:build` because `variant=deep`.

## Output layout

```
output/<topic-slug>/guide/
├── index.html              # hub page — title, intro, section cards linking to each section
├── section-01-<slug>.html  # one HTML per outline.sections[]
├── section-02-<slug>.html
└── ...
```

## index.html (the hub)

A single page that:
- Names the topic, level, and 1-sentence positioning (use outline.topic, config.level).
- Shows a **section grid**: one card per section, with the section title and the
  1-sentence summary from `outline.sections[].summary`.
- Each card links to `section-NN-<slug>.html` (relative path).
- Includes a **table of contents** at the top for quick jumping.
- No content from the sections themselves — the hub is purely navigation +
  topic framing.

## section-NN-<slug>.html (one per section)

Each section page is self-contained:
- **Header**: "← Back to overview" link to `index.html` (relative), section title.
- **Prev / Next nav**: at top AND bottom, linking to the adjacent sections by
  position. Disable the "Prev" link on section-01 and "Next" link on the last
  section. Use relative URLs.
- **Body**: render the matching markdown from `output/<slug>/sections/section-NN-<slug>.md`.
- **Diagram inlining**: where the source markdown has `<!-- DIAGRAM: ... -->`
  comments, replace with the actual inline `<svg>` or Mermaid block from
  `output/<slug>/diagrams/section-NN-<diagram-id>.{svg,mmd}`.
- **References** section at the bottom — render the source markdown's
  `## References` as a styled footnote block.

## Layout standards

- Max body width 760px centered (sections); the hub can use a wider grid (e.g. 1080px).
- Headings use the `--color-primary` accent for `<h2>` and `<h3>`.
- Inline code: `--color-surface` background, `--color-text` foreground, slight
  border radius.
- Code blocks: `--color-surface` background, syntax highlighting via inline
  styling on `<span>` tokens (no Prism/Highlight.js external dep).
- Mermaid: include the Mermaid CDN script `<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>` and call `mermaid.initialize({ theme: 'dark' })`. Only include this script on pages that actually contain a Mermaid block.

## File-naming rule

- Hub: literal `index.html`.
- Sections: `section-NN-<slug>.html` where NN is `01`, `02`, ... and slug
  matches outline.json. This pattern is what `/tg:promote` detects to identify
  a multi-page hub layout — do not deviate.

## Forbidden

- No `<div class="sws-quiz">…` blocks.
- No `chapter-NN.html` filenames.
- No external CSS files. Inline `<style>` in each page (DRY is fine via copy).
- No `<iframe>` for cross-section navigation (use real anchor links).

## When all HTML files are written

The dispatcher decides whether to auto-chain to `/tg:promote` or stop.
