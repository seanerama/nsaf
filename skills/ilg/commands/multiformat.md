---
name: ilg:multiformat
description: Process slides, transcripts, data sheets, or install guides into a learning guide
argument-hint: "[--focus 'topic'] [--difficulty level] [--audience 'description']"
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
Detect content type(s) from uploaded files, apply specialized analysis strategies,
and generate a single self-contained interactive HTML learning guide.

Supports: slide decks, presentation transcripts, product data sheets,
installation/configuration guides, and combinations thereof.

Produces: a single HTML file ready to open in any browser.
</objective>

<execution_context>
@~/.claude/ilg/workflows/single-session-multiformat.md
</execution_context>

<context>
Arguments: $ARGUMENTS

The user should have uploaded one or more files before running this command.
If no files are detected, ask them to upload their content.
</context>

<process>
1. Check that content files have been uploaded. If not, ask the user to upload them.

2. Parse any arguments:
   - `--focus "topic"` → focus quiz questions on a specific area
   - `--difficulty foundational|intermediate|advanced` → bias quiz difficulty
   - `--audience "description"` → adjust depth for target audience
   - `--scope "section"` → limit to specific sections (e.g., "slides 1-20")

3. Follow the workflow in `~/.claude/ilg/workflows/single-session-multiformat.md`:
   a. Detect content type(s) — slide deck, transcript, data sheet, install guide
   b. Apply content-type-specific analysis strategy
   c. Extract concepts, relationships, terms using universal extraction framework
   d. Generate quiz questions tailored to content type
   e. Build concept map with appropriate relationship types
   f. Compile glossary
   g. Generate the complete interactive HTML file

4. Save the HTML file and present it for download/preview.

5. Report: content type(s) detected, total concepts, quiz questions, glossary terms.
</process>
