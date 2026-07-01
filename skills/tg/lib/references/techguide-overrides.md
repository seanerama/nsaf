# Techguide Overrides (vs. SWS)

This file is the source of truth for what `/tg:*` does differently from `/sws:*`.
The `/tg:*` skill files are forks of `/sws:*` — when in doubt, follow these
overrides over the inherited SWS instructions.

## Variant selection (REQUIRED first step in /tg:start)

Read `techguide-config.json` in the project directory. The `variant` field is one of:

- **deep** — multi-section deep-dive HTML guide (5–12 sections; interactive elements throughout)
- **comparison** — head-to-head product/technology comparison with a feature matrix
- **explainer** — single-page deep explanation of one concept

If `variant` is missing, default to `deep`.

**Important:** All three variants should produce interactive HTML. The variant name describes STRUCTURE (single page vs hub-and-spoke vs head-to-head matrix), not whether interactivity exists. Comparisons should have sortable/filterable matrices; explainers should have animated SVGs; deep guides should have interactive nav and section transitions.

## Stage-by-stage variant behavior

| Stage | deep | comparison | explainer |
|---|---|---|---|
| `scope` | 5–12 sections (no "chapters" — these are sections) | Vendor list + 5–8 feature axes for the matrix | 3–5 concept blocks |
| `research` | Per section | Per vendor | Per concept block |
| `write` | Multi-section markdown; one .md per section under `output/<slug>/sections/` | One .md per vendor + one matrix.md under `output/<slug>/vendors/` | Single explainer.md under `output/<slug>/` |
| `diagrams` | 2–3 inline SVG/Mermaid per section | 1 architecture diagram per vendor + matrix highlights | 3–5 SVG diagrams (SVG-heavy) |
| `build` | Multi-HTML — `section-01.html`, `section-02.html`, …, plus `index.html` hub | Single HTML with sticky matrix + per-vendor anchored sections | Single rich HTML at `index.html`, SVG-heavy |

## What's REMOVED vs SWS

The following SWS concepts do NOT apply to techguides — skip them entirely:

- **No quizzes**. SWS injects `<div class="sws-quiz">…` blocks. Techguides do NOT have quizzes. If the inherited prompt mentions quizzes, omit those blocks.
- **No chapter numbering**. SWS uses `chapter-01.html`, `chapter-02.html`, … Techguides use `section-NN.html` (deep) or `index.html` (explainer / comparison).
- **No textbook companion**. SWS sometimes ships a `textbook.md` companion. Techguides don't have one.
- **No podcast prompt** (`/sws:podcast` doesn't have a `/tg:*` equivalent).
- **No slide deck** (`/sws:slides` doesn't have a `/tg:*` equivalent).
- **No `--chapters N` arg** to `/tg:start`. Use `--variant` and `--level` instead.

## Output layout

```
output/<slug>/
├── outline.json          # variant + section/vendor/concept list
├── research/             # per-target research notes
├── sections/             # variant=deep (one .md per section)
│   └── section-NN.md
├── vendors/              # variant=comparison
│   ├── vendor-X.md
│   └── matrix.md
├── explainer.md          # variant=explainer (one file)
├── diagrams/             # generated SVG / Mermaid sources
└── guide/                # FINAL HTML output — this is what tg:promote ships
    ├── index.html        # entry point (hub for deep; single page for explainer/comparison)
    ├── section-NN.html   # only for variant=deep
    └── assets/           # inline CSS already in each HTML; this dir is for images if any
```

## Dark mode from day one

The HTML in `guide/` MUST be authored dark on first pass. Do NOT rely on the
SWS `sed` dark-mode retrofit recipe — that exists for legacy SWS guides only.

Use the dark palette directly:
```css
--color-bg: #0a0a0f;
--color-surface: #1a1d2e;
--color-text: #e0e0e8;
--color-muted: #9ca3af;
--color-primary: #818cf8;
--color-primary-light: #1e1b4b;
--color-success: #4ade80;
--color-error: #f87171;
--color-border: #2a2f42;
```

## Promote target

The final guide is published to `seanmahoney.ai/guides/<slug>` (single-page or
hub). The complete promote recipe is at:

`/home/smahoney/seanmahoneyai/deploy-technical-guide.md`

`/tg:promote` reads that file as the single source of truth — do not duplicate
the recipe in skill prompts.

## sws-tools.cjs

The helper at `~/.claude/tg/bin/sws-tools.cjs` is a verbatim copy of the SWS
helper. Its sub-commands `outline-chapters` and `active-topic` are SWS-shaped.
For techguides, use them only if useful — `active-topic` works generically;
`outline-chapters` is for SWS multi-chapter layout and should be skipped.
