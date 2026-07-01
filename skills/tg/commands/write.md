---
description: Author techguide content from research; dispatches by variant
---

# /tg:write — Dispatcher

This is the **dispatcher** for the write stage. Read `techguide-config.json`
in the project directory, get the `variant` field, then **read and follow
the matching variant-specific write skill**:

| variant | Read and follow |
|---|---|
| `deep` | `~/.claude/commands/tg/write-deep.md` |
| `comparison` | `~/.claude/commands/tg/write-comparison.md` |
| `explainer` | `~/.claude/commands/tg/write-explainer.md` |

If `variant` is missing or unrecognized, default to `deep`.

## Inputs available
- `output/<slug>/outline.json` — the work breakdown produced by `/tg:scope`
- `output/<slug>/research/*.md` — the research material for each unit, produced by `/tg:research`
- `techguide-config.json` — `topic`, `level`, `notes`, `source_url`, `products[]`
- `source-material.md` / `source-material.pdf` — if `has_source_file: true`

## What each variant produces (summary; the variant skill has the detail)

| variant | Output location | Files |
|---|---|---|
| `deep` | `output/<slug>/sections/` | `section-NN-<slug>.md`, one per outline.sections[] |
| `comparison` | `output/<slug>/vendors/` | `vendor-<id>.md` (one per outline.products[]) + `matrix.md` (the cell data) |
| `explainer` | `output/<slug>/` | `explainer.md` (one file, all concept_blocks inline) |

When the variant-specific write step completes, **auto-chain to `/tg:diagrams`**.
Do not stop between stages.

## Forbidden in this stage
- Do NOT write into `chapters/` or `guides/` (SWS legacy directories — they may
  have been created by a previous skill but you should ignore them).
- Do NOT produce a `textbook.md` (SWS concept; techguides have no textbook companion).
- Do NOT write the HTML — that's `/tg:build`. This stage produces markdown only.
