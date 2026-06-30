# Auto Book Workflow

Automatically scan a book's structure, process all chapters, and build the
interactive HTML guide — all in one command. The user never needs to manually
chunk or run per-chapter commands.

## Phase 1: Scan and Plan

1. **Locate the table of contents.** Read the first ~20 pages to find the TOC.
   Record:
   - Book title and author
   - Every chapter title and its starting page number
   - Total number of chapters

2. **Determine page ranges.** For each chapter, calculate the page range:
   - Chapter N starts at its listed page and ends just before Chapter N+1 starts.
   - The last chapter ends at the final page of the book.

3. **Estimate book size.** Count total pages.
   - **Short book (under ~200 pages or ~8 chapters):** Use the single-session
     approach — read the full book in one pass. Follow
     `~/.claude/ilg/workflows/single-session-book.md` and skip to Phase 4.
   - **Long book (200+ pages or 8+ chapters):** Use the chunked approach below.

## Phase 2: Chunked Processing

Process the book chapter by chapter, building up structured relay files. Each
chapter is processed by a sub-agent to keep context windows clean.

### Step 1: Initialize (Preface + Chapter 1)

Spawn a sub-agent with the Agent tool to handle initialization:

**Agent prompt:**
```
You are processing a book to create an interactive learning guide.

Book file: [path to the uploaded PDF/EPUB]

Read ONLY the preface/introduction and Chapter 1 (pages [start]-[end]).

Follow the workflow instructions below exactly:

[Insert contents of ~/.claude/ilg/workflows/chunked-init.md]

Chapter index for progress.md:
[Insert the full chapter list with page ranges from Phase 1]

Save these three files to the working directory:
- progress.md
- summary.md
- learning-data.json
```

Wait for the agent to complete. Verify all three relay files were created.

### Step 2: Process Each Remaining Chapter

For each unprocessed chapter (2, 3, 4, ..., N), spawn a sub-agent:

**Agent prompt:**
```
You are processing Chapter [N]: "[Title]" of "[Book Title]".

Book file: [path to the uploaded PDF/EPUB]
Read ONLY pages [start]-[end].

Here are the current relay files:

--- progress.md ---
[Insert current contents of progress.md]

--- summary.md ---
[Insert current contents of summary.md]

--- learning-data.json ---
[Insert current contents of learning-data.json]

Follow the workflow instructions below exactly:

[Insert contents of ~/.claude/ilg/workflows/chunked-chapter.md]

Save the three updated files to the working directory:
- progress.md (with this chapter checked off)
- summary.md (with this chapter's section appended)
- learning-data.json (with this chapter's data appended)
```

After each agent completes:
- Read the updated relay files to verify they were written
- Report progress: "Chapter [N] of [total] processed"
- Continue to the next chapter

**Important:** Process chapters sequentially, not in parallel. Each chapter agent
needs the accumulated context from all previous chapters.

## Phase 3: Build

Once all chapters are processed (all checkboxes in progress.md are checked),
follow `~/.claude/ilg/workflows/chunked-build.md` to:

1. Validate the accumulated data (completeness, integrity, quality)
2. Fix any structural issues
3. Generate the complete interactive HTML file

This final build step runs in the main session (not a sub-agent) since it needs
to produce the HTML file for the user.

## Phase 4: Deliver

1. Save the HTML file with a descriptive name:
   `[book-title]-learning-guide.html` (kebab-case, no special characters)

2. Report final stats:
   - Chapters processed
   - Total concepts, relationships, quiz questions, glossary terms
   - Any data quality issues found and fixed
   - Any chapters flagged for thin coverage

3. Present the file for download/preview.

## Error Handling

- If a sub-agent fails or produces invalid JSON, retry that chapter once.
- If a chapter produces zero concepts or quiz questions, flag it but continue.
- If the TOC cannot be found, ask the user to specify chapter page ranges.
- If relay files are missing after a sub-agent, report the error and attempt
  to re-process that chapter.
