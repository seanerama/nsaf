---
name: tg:research
description: Research each chapter via Perplexity MCP (parallel sub-agents)
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Agent
  - Skill
---
<objective>
Research pipeline: read outline.json, spawn parallel sub-agents that each
query Perplexity MCP for one chapter's research material with citations.

Produces: output/{topic-slug}/research/chapter-{nn}.md (one per chapter)
</objective>

<execution_context>
@~/.claude/tg/prompts/research.md
@~/.claude/tg/references/pipeline-stages.md
@~/.claude/tg/references/mcp-setup.md
</execution_context>

<context>
Find active topic and list chapters:
```bash
node "$HOME/.claude/tg/bin/sws-tools.cjs" active-topic
node "$HOME/.claude/tg/bin/sws-tools.cjs" outline-chapters <topic-dir>
```
</context>

<process>
1. **Find active topic**:
   ```bash
   node "$HOME/.claude/tg/bin/sws-tools.cjs" active-topic
   ```
   - If no topic found or pipeline_stage is not "scoped:true", tell user to run `/tg:start` or `/tg:scope` first

2. **Read outline.json** from the topic directory

3. **Check for existing research files**:
   - For each chapter in outline, check if `research/chapter-{nn}.md` exists
   - Build a list of chapters that still need research
   - If all chapters already researched, skip to step 7

4. **Spawn parallel research sub-agents** via Agent tool:
   - Launch one Agent per un-researched chapter (use multiple Agent calls in a single message)
   - Each agent gets this prompt:

   ```
   You are a research agent for the Techguide learning pipeline.

   TASK: Research Chapter {N}: "{title}" for a textbook on "{topic}".

   Use the Perplexity MCP tools to search for information. For each research query below,
   call the Perplexity tool and compile the results.

   RESEARCH QUERIES:
   {list each research_query from outline.json for this chapter}

   ADDITIONAL CONTEXT:
   - Learning objectives for this chapter: {learning_objectives}
   - Key terms to ensure coverage of: {key_terms}

   For EACH query:
   1. Call the Perplexity MCP tool with the query
   2. Record the response content
   3. Record all citations/URLs returned

   After all queries are complete, write the research file to:
   {topic_dir}/research/chapter-{nn}.md

   USE THIS EXACT FORMAT:
   ---
   # Research: {Chapter Title}

   ## Query: {exact query text}

   {Full Perplexity response content — preserve everything}

   **Sources:**
   - [Source: {url1}]
   - [Source: {url2}]

   ---

   ## Query: {next query}

   {response}

   **Sources:**
   - [Source: {url}]

   ---

   ## Key Facts Summary

   - {Most important fact 1}
   - {Most important fact 2}
   - {Continue for 8-15 key facts}

   ## All Citations

   | # | URL | Context |
   |---|-----|---------|
   | 1 | {url} | {Brief note on what this source provided} |
   ---

   IMPORTANT:
   - Preserve ALL content from Perplexity responses — do not summarize or truncate
   - Preserve ALL citations — every URL matters for the writing stage
   - If a query returns no useful results, note that and suggest an alternative query
   - The Key Facts Summary should distill the most important learnable facts
   ```

5. **Wait for all sub-agents to complete**

6. **Verify all research files exist**:
   ```bash
   node "$HOME/.claude/tg/bin/sws-tools.cjs" status {slug}
   ```
   - If any chapters are missing, report which ones failed
   - Offer to retry failed chapters

7. **Update config.json** — read the file, update `pipeline_stage` to `"researched:true"`, write back

8. **Report to user**:
   ```
   Research complete for {topic}:
   - {N} chapters researched
   - {total citations} citations gathered
   ```

9. **Auto-invoke `/tg:write`** — IMMEDIATELY invoke via Skill tool. Do NOT just tell the user to run it.
</process>
