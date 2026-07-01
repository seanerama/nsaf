---
description: Build the outline for a techguide; dispatches by variant
---

# /tg:scope — Dispatcher

This is the **dispatcher** for the scope stage. Read `techguide-config.json` in
the project directory, get the `variant` field, then **read and follow the
matching variant-specific scope skill**:

| variant | Read and follow |
|---|---|
| `deep` | `~/.claude/commands/tg/scope-deep.md` |
| `comparison` | `~/.claude/commands/tg/scope-comparison.md` |
| `explainer` | `~/.claude/commands/tg/scope-explainer.md` |

If `variant` is missing or unrecognized, default to `deep`.

The variant-specific skill is solely responsible for producing
`output/<slug>/outline.json` in the correct shape and content for that variant.
Do **not** mix instructions from the other variant files.

When the variant-specific scope step completes, **auto-chain to `/tg:research`**.
Do not stop between stages.

## Inputs available
- `techguide-config.json` — `topic`, `variant`, `level`, `notes`, `source_url`, `products[]`, `has_source_file`
- `source-material.md` or `source-material.pdf` — if `has_source_file: true`, this is the primary source; outline MUST be derived from its substance

## Output
- `output/<topic-slug>/outline.json` — shape defined by the variant-specific skill
- `output/<topic-slug>/config.json` — same fields as `techguide-config.json`, plus `outline_version: 1`

## Forbidden in this stage
- No `chapters` arrays (SWS terminology — does not apply to techguides)
- No `outline-chapters` helper sub-command (it expects SWS shape)
- No quiz scaffolding (SWS-only)
