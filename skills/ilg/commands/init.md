---
name: ilg:init
description: Initialize chunked pipeline — read preface + Chapter 1, create relay files
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
First step of the chunked pipeline for long books. Read ONLY the preface/introduction
and Chapter 1, then create the three relay files that carry context across sessions.

Produces: progress.md, summary.md, learning-data.json
</objective>

<execution_context>
@~/.claude/ilg/workflows/chunked-init.md
@~/.claude/ilg/templates/learning-data.json
@~/.claude/ilg/templates/progress.md
@~/.claude/ilg/templates/summary.md
</execution_context>

<context>
The user should have uploaded a complete book (PDF or EPUB) before running this command.
If no file is detected, ask them to upload one.
</context>

<process>
1. Check that a PDF or EPUB has been uploaded. If not, ask the user to upload one.

2. Follow the workflow in `~/.claude/ilg/workflows/chunked-init.md`:
   a. Scan the table of contents — record all chapter titles and page numbers
   b. Read ONLY preface/introduction + Chapter 1 (do NOT read beyond)
   c. Create `progress.md` using the template — list ALL chapters from TOC
   d. Create `summary.md` using the template — book overview + Chapter 1 summary
   e. Create `learning-data.json` using the template — Chapter 1 data

3. Save all three relay files.

4. Report:
   - Book title, author, total chapters
   - Concepts, quiz questions, and glossary terms extracted from Chapter 1
   - Which chapter the next `/ilg:chapter` call should process

5. Remind the user: for the next session, upload the book AND all three relay files,
   then run `/ilg:chapter [N]`.
</process>
