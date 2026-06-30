---
name: sws:help
description: Show all StudyWS commands and pipeline overview
allowed-tools: []
---
<objective>
Display all available /sws:* commands with descriptions and show the pipeline flow.
</objective>

<process>
Display the following to the user:

# StudyWS — Help

## Pipeline Commands (run in order)

| Command | Description |
|---------|-------------|
| `/sws:start` | Name a topic + set learning style preferences |
| `/sws:scope` | Interactively build a chapter outline |
| `/sws:research` | Research each chapter via Perplexity (parallel) |
| `/sws:write` | Write textbook chapters from research (parallel) |
| `/sws:diagrams` | Add mermaid diagrams to chapters (parallel) |
| `/sws:guide` | Generate interactive HTML study guides with quizzes (parallel) |
| `/sws:slides` | Generate slide descriptions for deck creation |
| `/sws:podcast` | Generate podcast prompt from slides + textbook |

## On-Demand Commands

| Command | Description |
|---------|-------------|
| `/sws:review` | Opus 4 coherence review of the full textbook |
| `/sws:status` | Show pipeline progress for all topics |
| `/sws:help` | Show this help |

## Pipeline Flow

```
/sws:start → /sws:scope → /sws:research → /sws:write → /sws:diagrams → /sws:guide → /sws:slides → /sws:podcast
```

Each pipeline command auto-invokes the next on completion. Start with `/sws:start` and the pipeline flows automatically.

## Output

All generated content goes to `output/{topic-slug}/` in the current directory:
- `textbook.md` — full textbook with diagrams
- `guides/chapter-{nn}.html` — interactive study guides with quizzes
- `slides.md` — slide descriptions
- `podcast-prompt.md` — podcast generation prompt

## On-Demand Review

Run `/sws:review` at any time after chapters are written to get an Opus 4 quality assessment.
</process>
