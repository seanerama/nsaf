---
description: Render techguide HTML; dispatches by variant
---

# /tg:build — Dispatcher

This is the **dispatcher** for the build (HTML render) stage. Read
`techguide-config.json` in the project directory, get the `variant` field,
then **read and follow the matching variant-specific build skill**:

| variant | Read and follow |
|---|---|
| `deep` | `~/.claude/commands/tg/build-deep.md` |
| `comparison` | `~/.claude/commands/tg/build-comparison.md` |
| `explainer` | `~/.claude/commands/tg/build-explainer.md` |

If `variant` is missing or unrecognized, default to `deep`.

## Inputs available
- `output/<slug>/outline.json` — the work breakdown
- `output/<slug>/{sections|vendors|explainer.md}` — the markdown content (location depends on variant)
- `output/<slug>/diagrams/` — SVG/Mermaid sources from `/tg:diagrams`
- `techguide-config.json` — `topic`, `level`, etc.

## What each variant produces

All variants land HTML at `output/<slug>/guide/`. This directory is what
`/tg:promote` will ship to `seanmahoney.ai/guides/`.

| variant | Output shape |
|---|---|
| `deep` | `guide/index.html` (hub) + `guide/section-NN-<slug>.html` (multi-page) |
| `comparison` | `guide/index.html` (single-page with sticky matrix + anchored vendor sections) |
| `explainer` | `guide/index.html` (single rich page, SVG-heavy) |

## Dark mode from day one

All variants MUST author the HTML dark on first pass. Use this palette
(matches the seanmahoney.ai dark theme):

```css
:root {
  --color-bg: #0a0a0f;
  --color-surface: #1a1d2e;
  --color-text: #e0e0e8;
  --color-muted: #9ca3af;
  --color-primary: #818cf8;
  --color-primary-light: #1e1b4b;
  --color-success: #4ade80;
  --color-error: #f87171;
  --color-border: #2a2f42;
}
```

Do NOT rely on the SWS `sed` dark-mode retrofit recipe — that exists for
legacy SWS guides only.

## Forbidden in this stage
- No `chapters/` directory in the output (SWS legacy).
- No SWS quiz blocks (`<div class="sws-quiz">…`).
- No CDN dependencies except Mermaid (and only when actually used).
- No external CSS files — inline `<style>` per HTML page.

## When build is done

Return control to the parent dispatcher. **Auto-chain to `/tg:promote`** if
the project is being run in auto-deploy mode; otherwise stop here and report
the path to `guide/`.
