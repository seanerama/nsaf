# Chunked Pipeline: Initialization Workflow

You are the first agent in a multi-session learning guide pipeline. You have been given a complete book. Your job is to read ONLY the preface/introduction and Chapter 1, extract structured learning data, and create the foundational relay files that subsequent sessions will build on.

**IMPORTANT:** Do NOT read beyond Chapter 1. Stay within your assigned scope to keep the context window lean. Later `/ilg:chapter` calls will handle the remaining chapters.

## Tasks

### 1. Scan the Table of Contents
Before reading any content, locate the table of contents and record:
- Book title and author
- Total number of chapters
- All chapter titles and page numbers (if available)

This information is critical for the progress tracker and for future sessions to know where each chapter starts and ends.

### 2. Read and Analyze (Preface/Introduction + Chapter 1 ONLY)
- Read the preface/introduction to understand the book's overall purpose, audience, and structure
- Read Chapter 1 thoroughly
- Identify the author's core thesis and what the book promises to deliver
- Extract all key concepts, terms, and relationships from Chapter 1
- **Stop reading after Chapter 1 ends**

### 3. Create: progress.md

Use the template at `~/.claude/ilg/templates/progress.md` as a starting point.

Populate:
- Book info (title, author, total chapters, purpose)
- Complete chapter index with ALL chapters from the table of contents
- Mark preface/introduction and Chapter 1 as processed
- Add processing notes for the next session

### 4. Create: summary.md

Use the template at `~/.claude/ilg/templates/summary.md` as a starting point.

Populate:
- Book overview (2-3 paragraphs from preface/introduction)
- Chapter 1 section: key ideas, connections, critical context for later chapters

### 5. Create: learning-data.json

Use the template at `~/.claude/ilg/templates/learning-data.json` as a starting point.

Populate:
- Book metadata
- Chapter 1 entry in the chapters array
- All concepts from Chapter 1 (IDs: `c1-001`, `c1-002`, ...)
- Relationships between Chapter 1 concepts
- At least 5 quiz questions (IDs: `q1-001`, `q1-002`, ...)
- All domain-specific or author-defined terms (IDs: `t1-001`, `t1-002`, ...)

### 6. Extraction Targets for Chapter 1
- **Concepts:** Every meaningful concept (typically 5-15 per chapter)
- **Relationships:** How concepts connect to each other within the chapter
- **Quiz questions:** At least 5, spread across difficulty levels
- **Glossary terms:** Every domain-specific or author-defined term

### 7. Before You Finish
Confirm:
- [ ] All three files are created and saved
- [ ] The chapter index in progress.md lists ALL chapters from the table of contents
- [ ] JSON is valid and well-structured
- [ ] You did NOT read beyond Chapter 1

State which chapter the next `/ilg:chapter` call should process and any guidance for that session.
