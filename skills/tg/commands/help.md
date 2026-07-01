# /tg — Techguide pipeline command index

The `/tg:*` skill set builds technical guides for seanmahoney.ai/guides.
A techguide is one of three variants chosen per topic:

- **deep** — multi-section deep-dive HTML guide (interactive throughout)
- **comparison** — head-to-head product comparison with a feature matrix
- **explainer** — single-page deep explanation of one concept

## Pipeline (auto-chains)

1. `/tg:start` — load `techguide-config.json`, dispatch on variant
2. `/tg:scope` — outline (sections / vendors / concept blocks)
3. `/tg:research` — parallel research per section/vendor/concept
4. `/tg:write` — author long-form markdown
5. `/tg:diagrams` — inline SVG/Mermaid diagrams
6. `/tg:build` — render final dark-mode HTML into `output/<slug>/guide/`
7. `/tg:promote` — publish via `deploy-technical-guide.md`

## Other commands

- `/tg:status` — show pipeline progress
- `/tg:review` — QA pass on the rendered guide
- `/tg:help` — this page

## Differences from /sws:*

See `~/.claude/tg/references/techguide-overrides.md`. Summary:
- No quizzes, no chapter numbering, no textbook companion
- No slides, no podcast
- Output layout differs by variant
- Promote target is `src/content/guides/` (not `src/content/studyGuides/`)
