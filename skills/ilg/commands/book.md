---
name: ilg:book
description: Process a book into an interactive learning guide (auto-chunks long books)
argument-hint: "[--chapters X-Y] [--focus 'topic'] [--difficulty level] [--quiz-depth N]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Agent
  - AskUserQuestion
---
<objective>
Read an uploaded book (PDF or EPUB), automatically detect chapters, process them
in sequence (using sub-agents for long books), and generate a single self-contained
interactive HTML learning guide with concept map, quiz engine, and glossary explorer.

The user does NOT need to manually chunk the book — this command handles everything.

Produces: a single HTML file ready to open in any browser.
</objective>

<execution_context>
@~/.claude/ilg/workflows/auto-book.md
@~/.claude/ilg/workflows/single-session-book.md
@~/.claude/ilg/workflows/chunked-init.md
@~/.claude/ilg/workflows/chunked-chapter.md
@~/.claude/ilg/workflows/chunked-build.md
@~/.claude/ilg/templates/learning-data.json
@~/.claude/ilg/templates/progress.md
@~/.claude/ilg/templates/summary.md
</execution_context>

<context>
Arguments: $ARGUMENTS

The user should have uploaded a PDF or EPUB before running this command.
If no file is detected, ask them to upload one.
</context>

<process>
1. Check that a PDF or EPUB has been uploaded or is available. If not, ask the user to upload one.

2. Parse any arguments:
   - `--chapters X-Y` → scope to specific chapters
   - `--focus "topic"` → give extra depth to a topic area
   - `--difficulty foundational|intermediate|advanced` → bias quiz difficulty
   - `--quiz-depth N` → questions per chapter (default: 5)

3. Follow the workflow in `~/.claude/ilg/workflows/auto-book.md` to automatically
   scan, chunk, process, and build the guide.

4. Save the HTML file and present it for download/preview.

5. Report stats: total concepts, relationships, quiz questions, glossary terms.
</process>
