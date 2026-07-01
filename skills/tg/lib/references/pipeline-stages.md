# SWS Pipeline Stages

## Pipeline Flow

```
/sws:start → /sws:scope → /sws:research → /sws:write → /sws:diagrams → /sws:guide → /sws:slides → /sws:podcast
```

Each command auto-invokes the next on completion.

## Stage Details

| # | Command | Parallelism | Input | Output |
|---|---------|-------------|-------|--------|
| 1 | `/sws:start` | None | User input | config.json |
| 2 | `/sws:scope` | None | config.json | outline.json |
| 3 | `/sws:research` | Sub-agents per chapter | outline.json | research/chapter-{nn}.md |
| 4 | `/sws:write` | Sub-agents per chapter | research + outline | chapters/chapter-{nn}.md, textbook.md |
| 5 | `/sws:diagrams` | Sub-agents per chapter | chapters | Updated chapters + textbook.md |
| 6 | `/sws:guide` | Sub-agents per chapter | chapters + outline | guides/chapter-{nn}.html |
| 7 | `/sws:slides` | Single pass | chapters + outline | slides.md |
| 8 | `/sws:podcast` | Single pass | slides.md + textbook.md | podcast-prompt.md |

## On-Demand

| Command | Trigger | Output |
|---------|---------|--------|
| `/sws:review` | Manual | review-report.md |
| `/sws:status` | Manual | Terminal output |

## Resumability

All stages check for existing output files before running. If a file exists, its corresponding work is skipped. To re-run a specific chapter's stage, delete its output file and re-run the command.
