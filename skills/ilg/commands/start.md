---
name: ilg:start
description: Choose a workflow and begin building an interactive learning guide
argument-hint: "[book|multiformat|chunked]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
---
<objective>
Help the user choose the right workflow and kick it off.

Usage:
  /ilg:start              — interactive (asks what you have)
  /ilg:start book         — single-session book workflow
  /ilg:start multiformat  — single-session multi-format workflow
  /ilg:start chunked      — multi-session chunked pipeline for long books
</objective>

<process>
1. If no argument provided, ask the user:

   **What kind of content are you working with?**

   1. **Book (PDF/EPUB)** that fits in one session → `/ilg:book`
   2. **Non-book content** (slides, transcript, data sheet, install guide) → `/ilg:multiformat`
   3. **Long book** that needs chapter-by-chapter processing → `/ilg:init` (starts chunked pipeline)

2. Based on their choice, immediately invoke the matching command:
   - Choice 1 → invoke `/ilg:book`
   - Choice 2 → invoke `/ilg:multiformat`
   - Choice 3 → invoke `/ilg:init`

3. Do NOT just display instructions — invoke the next command directly.
</process>
