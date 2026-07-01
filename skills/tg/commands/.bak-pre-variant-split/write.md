---
name: tg:write
description: Write textbook chapters from research (parallel sub-agents)
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Agent
  - Skill
---
<objective>
Chapter writing pipeline: spawn parallel sub-agents that each transform
one chapter's research into polished textbook content, then concatenate
into textbook.md.

Produces: output/{topic-slug}/chapters/chapter-{nn}.md, output/{topic-slug}/textbook.md
</objective>

<execution_context>
@~/.claude/tg/prompts/writing.md
@~/.claude/tg/references/pipeline-stages.md
@~/.claude/tg/templates/chapter.md
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
   - Verify pipeline_stage is "researched:true", otherwise direct user to run earlier commands

2. **Read outline.json** and **config.json**

3. **Check for existing chapter files**:
   - For each chapter, check if `chapters/chapter-{nn}.md` exists
   - Build list of chapters needing writing
   - If all exist, skip to step 6

4. **Spawn parallel writing sub-agents** via Agent tool:
   - One Agent per un-written chapter (multiple Agent calls in a single message)
   - Each agent gets this prompt:

   ```
   You are an expert educational author writing a textbook chapter for the
   Techguide learning pipeline.

   TASK: Write Chapter {N}: "{title}" for a textbook on "{topic}".

   LEARNING STYLE PREFERENCES:
   - Depth: {depth}
   - Include worked examples: {examples}
   - Include real-world analogies: {analogies}
   - Visual emphasis: {visual_emphasis}

   CHAPTER STRUCTURE (from outline):
   Learning Objectives:
   {learning_objectives as bullet list}

   Sections:
   {for each section: title + sub_topics}

   Key Terms:
   {key_terms}

   RESEARCH MATERIAL:
   {read and paste the full contents of research/chapter-{nn}.md}

   WRITING STANDARDS:
   - Use the research as your factual foundation — do NOT invent facts
   - Cite sources inline using [Source: url] notation from the research
   - Target 2,500-5,000 words depending on section count
   - Assume the reader is intelligent but new to this topic
   - Define technical terms the first time they appear
   - Every major concept needs a concrete real-world example (if examples=true)
   - Use analogies to connect unfamiliar concepts to familiar ones (if analogies=true)
   - End each section with: > **Key Takeaway:** {2-3 sentence recap}

   REQUIRED FORMAT:
   ```markdown
   ## Chapter {N}: {Title}

   ### Learning Objectives

   - {objective 1}
   - {objective 2}

   ### {Section Title}

   #### {Sub-topic}

   {Content paragraphs with [Source: url] citations}

   > **Key Takeaway:** {recap}

   ### Chapter Summary

   {2-3 paragraph synthesis}

   ### Key Terms

   | Term | Definition |
   |------|-----------|
   | {term} | {clear definition} |
   ```

   Write the file to: {topic_dir}/chapters/chapter-{nn}.md

   IMPORTANT:
   - Follow the heading hierarchy exactly: ## chapter, ### section, #### sub-topic
   - Do NOT include a top-level # heading — that's reserved for the textbook title
   - Preserve inline citations from the research — every [Source: url] matters
   - The Key Terms table should include ALL key_terms from the outline
   ```

5. **Wait for all sub-agents, then assemble textbook.md**:
   - Read all chapter files in order
   - Build table of contents with anchor links
   - Concatenate with `---` separators
   - Write `textbook.md`:

   ```markdown
   # {title from outline.json}

   {description from outline.json}

   ## Table of Contents

   {for each chapter: "- [Chapter N: Title](#chapter-n-title)"}

   ---

   {all chapters concatenated}
   ```

6. **Verify**:
   ```bash
   node "$HOME/.claude/tg/bin/sws-tools.cjs" status {slug}
   ```
   - Confirm all chapter files exist
   - Confirm textbook.md exists

7. **Update config.json** — set pipeline_stage to "written:true"

8. **Report**: "{N} chapters written, textbook.md assembled ({word_count} words estimated)"

9. **Auto-invoke `/tg:diagrams`** — IMMEDIATELY invoke via Skill tool.
</process>
