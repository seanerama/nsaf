---
name: ilg:status
description: Show current chunked pipeline progress
allowed-tools:
  - Read
  - Glob
  - Bash
---
<objective>
Display the current state of a chunked pipeline — which chapters have been processed,
how much data has been collected, and what to do next.
</objective>

<process>
1. Look for relay files in the current directory or uploaded files:
   - `progress.md`
   - `learning-data.json`
   - `summary.md`

2. If no relay files found:
   - Report: "No chunked pipeline in progress. Run `/ilg:init` to start one, or use `/ilg:book` for a single-session workflow."

3. If relay files found, read them and display:

   ## Pipeline Status

   **Book:** [title] by [author]
   **Total Chapters:** [N]

   ### Processing Progress
   [Show the chapter checklist from progress.md]

   ### Data Collected So Far
   | Metric | Count |
   |--------|-------|
   | Concepts | [N] |
   | Relationships | [N] |
   | Quiz Questions | [N] |
   | Glossary Terms | [N] |

   ### Next Step
   - If chapters remain: "Run `/ilg:chapter [N]` to process [Chapter Title]"
   - If all chapters done: "All chapters processed! Run `/ilg:build` to generate the HTML guide."
</process>
