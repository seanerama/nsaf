---
name: sws:slides
description: Generate detailed slide descriptions for a deck-creation agent
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Skill
---
<objective>
Generate slide descriptions covering the full topic — one markdown file
with detailed per-slide specs that a deck-creation agent can execute.

Produces: output/{topic-slug}/slides.md
</objective>

<execution_context>
@~/.claude/sws/prompts/slides.md
@~/.claude/sws/references/pipeline-stages.md
</execution_context>

<context>
```bash
node "$HOME/.claude/sws/bin/sws-tools.cjs" active-topic
```
</context>

<process>
1. **Find active topic** and verify chapters are written

2. **Read outline.json** and **all chapter files** from chapters/

3. **Load slides prompt** from ~/.claude/sws/prompts/slides.md

4. **Generate slides.md** in a single pass (no sub-agents):

   For each chapter, produce slides following this structure:

   ```markdown
   # Slide Deck: {Textbook Title}

   Total slides: {estimate}
   Estimated presentation time: {N} minutes

   ---

   ## Chapter 1: {Title}

   ### Slide 1.1: Title Slide
   - **Type:** Title
   - **Title:** {chapter title}
   - **Subtitle:** {chapter's primary learning objective}
   - **Visual:** {background imagery description — be specific about colors, style}
   - **Notes:** {1 sentence on what this chapter covers}

   ### Slide 1.2: {Key Concept Name}
   - **Type:** Content
   - **Visual:** {detailed description of diagram/graphic/image to show}
   - **Bullet Points:**
     - {Point 1 — concise, max 10 words}
     - {Point 2}
     - {Point 3}
   - **Speaker Notes:** {2-3 sentences explaining what to say with this slide}
   - **Transition:** {how to bridge to the next slide}

   ### Slide 1.3: {Diagram Slide}
   - **Type:** Diagram
   - **Visual:** {reference mermaid diagram from chapter: "Figure 1.2: ..."}
   - **Caption:** {figure description}
   - **Speaker Notes:** {how to walk through the diagram}

   ### Slide 1.4: {Example/Case Study}
   - **Type:** Example
   - **Visual:** {code snippet, screenshot description, or illustration}
   - **Content:** {the example or case study in brief}
   - **Speaker Notes:** {how to present this example}

   ...

   ### Slide 1.N: Chapter {N} Takeaways
   - **Type:** Summary
   - **Key Points:**
     - {Takeaway 1}
     - {Takeaway 2}
     - {Takeaway 3}
   - **Transition to next chapter:** {bridging statement}

   ---

   ## Chapter 2: {Title}
   ...
   ```

   SLIDE COUNT GUIDELINES:
   - Title slide: 1 per chapter
   - Content slides: 3-6 per section (depends on complexity)
   - Diagram slides: 1 per mermaid diagram in the chapter
   - Example slides: 1-2 per chapter (for worked examples)
   - Summary slide: 1 per chapter
   - Total estimate: 8-15 slides per chapter

5. **Write slides.md** to output/{slug}/

6. **Update config.json** — set pipeline_stage to "slides:true"

7. **Report**: "Generated slide descriptions: {total slides} slides across {N} chapters"

8. **Auto-invoke `/sws:podcast`** — IMMEDIATELY invoke via Skill tool.
</process>
