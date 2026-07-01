---
description: Render variant=comparison — single page with sticky matrix + vendor sections
---

# /tg:build-comparison — Render the single-page comparison

You were dispatched here from `/tg:build` because `variant=comparison`.

## Output layout

```
output/<topic-slug>/guide/
└── index.html              # ONE FILE — all matrix + vendor writeups inline
```

A comparison is a **single page**. No multi-file hub. The reader scrolls
through the matrix and the vendor narratives in one document. The promote
step ships this as `public/guides/<slug>.html` (single-page form).

## Page structure

```
┌──────────────────────────────────────────────────────┐
│  TITLE + 1-paragraph thesis                          │
│  (outline.topic + an intro you compose)              │
├──────────────────────────────────────────────────────┤
│  MATRIX (sticky-positioned within the page)          │
│  - rows = products, columns = axes                   │
│  - sortable on click (any column)                    │
│  - filterable (optional: a row-filter input)         │
│  - each product name links to its vendor section     │
│    further down the page (anchored)                  │
├──────────────────────────────────────────────────────┤
│  SCORING RUBRIC                                      │
│  - render outline.scoring_rubric verbatim            │
├──────────────────────────────────────────────────────┤
│  PER-VENDOR SECTIONS — one <section id="..."> each   │
│  - title, positioning, Where it wins, Where it       │
│    doesn't, When to pick it, References              │
│  - rendered from output/<slug>/vendors/vendor-<id>.md │
└──────────────────────────────────────────────────────┘
```

## Matrix rendering

- Render the cells from `output/<slug>/vendors/matrix.md`'s frontmatter `cells` map.
- **Sortable**: clicking a column header sorts the table by that axis.
  Use vanilla JS — no external sort library. The axis's `sort` field
  (`desc-better`, `asc-better`, `categorical`) determines default direction.
- **Best-cell highlighting**: in quantitative columns, the "best" cell per axis
  gets `class="cell-best"` with a subtle `--color-success`-tinted background.
- **Unknown cells**: render literally as "unknown" in muted color (`--color-muted`).
- **Per-cell notes**: where matrix.md has a "Matrix notes" entry for a specific
  product × axis, add a small `(i)` indicator next to the cell that reveals
  the note on hover (use a native `<details>` or a CSS `:hover` tooltip).

## Vendor sections

For each product in outline order:

```html
<section id="vendor-<id>" class="vendor-section">
  <h2>{vendor name}</h2>
  <p class="positioning">{1–2 sentence positioning from outline}</p>

  <h3>What it is</h3>
  ... (render vendor-<id>.md body) ...

  <h3>Where it wins</h3>
  ...

  <h3>Where it doesn't</h3>
  ...

  <h3>When to pick it</h3>
  ...

  <h3>References</h3>
  ...
</section>
```

The matrix links (each product name) jump to `#vendor-<id>`.

## Diagram inlining

If `output/<slug>/diagrams/` has a per-vendor diagram (e.g. an architecture
sketch), inline it under the vendor's "What it is" subsection. The
comparison page is matrix-first — diagrams are supporting, not central.

## Layout standards

- Max body width 1200px centered (the matrix needs room).
- Matrix uses `position: sticky; top: 0` so it stays visible as the reader
  scrolls through vendor sections.
- Use semantic `<table>` for the matrix, `<section>` for each vendor.
- Inline `<style>` and `<script>` only — no external CSS or JS files.

## File-naming rule

- Single file at `output/<slug>/guide/index.html`.
- This single-file shape is what `/tg:promote` detects as the comparison/explainer
  layout — it ships the page as `public/guides/<slug>.html`.

## Forbidden

- No multi-page split. The matrix MUST be on the same page as the vendor sections.
- No "Verdict" or "Our pick" section.
- No external JS libraries — vanilla DOM + Array.prototype.sort.
- No `<div class="sws-quiz">…` blocks.

## When index.html is written

The dispatcher decides whether to auto-chain to `/tg:promote` or stop.
