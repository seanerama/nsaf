---
name: ilg:build
description: Final build — compile relay files into the interactive HTML learning guide
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
---
<objective>
Final step of the chunked pipeline. Validate all accumulated data from the relay files
and compile it into a polished, interactive HTML learning guide.

Requires: progress.md, summary.md, learning-data.json (from /ilg:init + /ilg:chapter runs)
Produces: a single HTML file ready to open in any browser.
</objective>

<execution_context>
@~/.claude/ilg/workflows/chunked-build.md
</execution_context>

<context>
The user should have uploaded the three relay files:
- summary.md — complete running summary of all chapters
- learning-data.json — all concepts, relationships, quiz questions, glossary terms
- progress.md — confirms processing status of all chapters

The book itself is NOT needed for this step.
</context>

<process>
1. Verify all three relay files are available. If missing, tell the user what to upload.

2. Follow the workflow in `~/.claude/ilg/workflows/chunked-build.md`:
   a. Validate completeness — all chapters processed?
   b. Validate integrity — orphaned references, duplicates, missing fields?
   c. Validate quality — sparse chapters, isolated concepts?
   d. Fix any structural issues found
   e. Generate the complete interactive HTML file with all three panels

3. Save the HTML file and present it for download/preview.

4. Report:
   - Data validation results (issues found and fixed)
   - Total concepts, relationships, quiz questions, glossary terms
   - Any chapters flagged for thin coverage
</process>
