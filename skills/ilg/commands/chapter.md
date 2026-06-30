---
name: ilg:chapter
description: Process the next chapter in the chunked pipeline
argument-hint: "[chapter-number] '[chapter-title]'"
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
Process ONE chapter of a long book, appending structured data to the existing
relay files. Part of the chunked pipeline (run after /ilg:init).

Updates: progress.md, summary.md, learning-data.json
</objective>

<execution_context>
@~/.claude/ilg/workflows/chunked-chapter.md
</execution_context>

<context>
Chapter: $ARGUMENTS

The user should have uploaded:
1. The full book (PDF or EPUB)
2. The three relay files: summary.md, learning-data.json, progress.md

If the chapter number is not specified, read progress.md to determine the next
unprocessed chapter.
</context>

<process>
1. Verify all required files are available (book + 3 relay files). If missing, tell
   the user what to upload.

2. If no chapter number specified, read progress.md to find the next unchecked chapter.

3. Follow the workflow in `~/.claude/ilg/workflows/chunked-chapter.md`:
   a. Orient: read progress.md for page range, summary.md for narrative context,
      skim learning-data.json for existing concepts/terms
   b. Read ONLY the assigned chapter
   c. Append to summary.md (do NOT modify existing sections)
   d. Append to learning-data.json (new concepts, relationships, quizzes, terms)
   e. Update progress.md (check off the chapter)

4. Save all three updated relay files.

5. Report:
   - Chapter processed
   - New concepts, quiz questions, glossary terms added
   - Key cross-chapter connections discovered
   - Which chapter to process next (or if all chapters are done, suggest `/ilg:build`)
</process>
