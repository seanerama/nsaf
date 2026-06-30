# SWS Output Formats

## Directory Structure

```
output/{topic-slug}/
├── config.json              # Topic metadata + learning style
├── outline.json             # Chapter hierarchy from scoping
├── research/
│   └── chapter-{nn}.md      # Perplexity research per chapter
├── chapters/
│   └── chapter-{nn}.md      # Written chapters (with diagrams after /sws:diagrams)
├── textbook.md              # Concatenated chapters with TOC
├── guides/
│   └── chapter-{nn}.html    # Interactive study guides
├── slides.md                # Slide descriptions
├── podcast-prompt.md        # Podcast generation prompt
└── review-report.md         # On-demand quality review
```

## File Naming

- **Topic slugs:** lowercase, hyphens only (e.g., `kubernetes-networking`)
- **Chapter files:** `chapter-{nn}` with zero-padded two digits (e.g., `chapter-01`, `chapter-12`)

## Markdown Heading Hierarchy

- `#` — Textbook title only
- `##` — Chapter title
- `###` — Section
- `####` — Sub-section

## Citation Format

Inline: `[Source: url]`

## Diagram Labels

`**Figure {chapter}.{n}: {description}**` immediately above mermaid code blocks.
