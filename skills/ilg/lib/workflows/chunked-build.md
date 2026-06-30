# Chunked Pipeline: Final Build Workflow

You are the final build agent in a multi-session learning guide pipeline. All chapters have been processed by previous sessions. Your job is to compile the structured learning data into a polished, interactive HTML learning guide.

## Inputs
You should have:
1. `summary.md` — complete running summary of all chapters
2. `learning-data.json` — all concepts, relationships, quiz questions, and glossary terms
3. `progress.md` — confirms processing status of all chapters

The book itself is NOT needed for this step.

## Tasks

### 1. Validate the Data

Before building anything, run these checks and report findings:

**Completeness:**
- Are all chapters marked as processed in progress.md?
- Does every chapter have at least 1 entry in concepts, quizQuestions, and glossaryTerms?

**Integrity:**
- Are there orphaned relationships (referencing concept IDs that don't exist)?
- Are there duplicate glossary terms?
- Do all quiz questions have required fields (question, options, correctAnswer, explanation)?
- Are concept IDs unique across the entire dataset?

**Quality:**
- Are there chapters with significantly fewer concepts or questions than others? (Flag for awareness)
- Are there cross-chapter relationships, or is each chapter isolated? (Isolated = weaker concept map)

Report findings. Fix structural issues (orphaned references, duplicates, missing fields). If a chapter is missing entirely, note it clearly — do not invent content.

### 2. Generate the Interactive HTML Learning Guide

Build a single, self-contained HTML file:

#### Header
- Book title and author (from learning-data.json)
- Total chapters covered
- Stats bar: X concepts · Y quiz questions · Z glossary terms
- Dark mode toggle

#### Navigation
- Tabbed interface switching between three panels
- "Study Progress" button accessible from any panel

#### Panel 1: Concept Map (Interactive Knowledge Graph)

**Graph rendering:**
- Use a CDN-loaded graph library (Cytoscape.js, vis.js, or D3-force)
- Render all concepts as nodes, all relationships as edges
- Node size scaled by number of connections

**Node styling:**
- Color-coded by chapter (distinct color per chapter)
- Shape by importance: foundational = circle, supporting = rounded rectangle, advanced = diamond
- Label shows concept name

**Edge styling by relationship type:**
- `builds-on` → solid arrow, neutral color
- `contrasts-with` → dashed line, orange
- `example-of` → dotted arrow, green
- `part-of` → thick solid line, blue
- `enables` → solid arrow, purple
- Cross-chapter edges visually distinct (thicker or different opacity)

**Interactions:**
- Click node: detail panel with definition, chapter, importance, connected concepts highlighted
- Hover: preview concept name and chapter

**Controls:**
- Chapter filter dropdown
- Toggle: color by chapter vs importance
- Toggle: Learning Path mode (breadth-first from foundational → advanced)
- Reset View button
- Zoom and pan

#### Panel 2: Quiz & Knowledge Checks

**Question types:**
- **Multiple choice** — 4 radio options + submit
- **True/False** — two radios + explanation text field
- **Scenario-based** — longer prompt + multiple choice
- **Fill-in-the-blank** — text input with case-insensitive fuzzy matching (1 edit distance)

**Filters:** Chapter, Difficulty, Concept Area

**Feedback per question:**
- Correct/incorrect with color indicator
- Explanation text
- Why each wrong answer is wrong (multiple choice)
- Source reference
- Next Question button

**Modes:** Full Quiz, Chapter Quiz, Quick Check (10 random), Retry Missed

**Score tracking:** Running score, progress bar, persists across mode switches

#### Panel 3: Key Term Explorer (Glossary)

**Browse modes:** Alphabetical (A-Z with letter jumps), By Chapter

**Term cards:** Term name (bold), definition, author usage, related terms (clickable), example/analogy

**Search:** Live filtering by term name, definition, and example fields

**Flashcard mode:** Show term → reveal definition, Got it / Still learning, shuffle, mastery counter

**Bookmarking:** Star toggle, "Review Later" filter

#### Study Progress Overlay
- Concept Map: X of Y concepts explored
- Quiz: score, questions attempted vs total
- Glossary: terms viewed vs total, flashcard mastery
- Quick-jump buttons to each panel

### 3. Design Requirements

**Visual:** Clean, modern, distraction-free. Consistent color scheme. Readable typography (system font stack). Smooth transitions.

**Dark mode:** Toggle in header. All elements respect the mode.

**Responsiveness:** Desktop + tablet. Concept map scrollable/zoomable on smaller screens. Quiz and glossary stack on narrow viewports.

**Technical:**
- Single self-contained HTML file (all CSS and JS inline)
- External libraries from CDN only (e.g., cdnjs.cloudflare.com)
- No build tools or frameworks
- Opens in any modern browser (Chrome, Firefox, Safari, Edge)
- All data embedded as JavaScript objects
