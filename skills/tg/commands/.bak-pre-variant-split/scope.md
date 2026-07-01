---
name: tg:scope
description: Interactively build a chapter outline for the current topic
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
  - Skill
---
<objective>
Interactive scoping session: read the topic config, propose a chapter outline,
refine it with the user, and write outline.json.

Produces: output/{topic-slug}/outline.json
</objective>

<execution_context>
@~/.claude/tg/prompts/scoping.md
@~/.claude/tg/references/pipeline-stages.md
</execution_context>

<context>
Find the active topic:
```bash
node "$HOME/.claude/tg/bin/sws-tools.cjs" status
```
Read its config.json for topic and learning style.
</context>

<process>
1. **Find active topic**:
   ```bash
   node "$HOME/.claude/tg/bin/sws-tools.cjs" status
   ```
   - Find the most recent topic that has `config: true` but `outline: false`
   - If no such topic exists, check for topics with `config: true` and ask which to re-scope
   - If no topics at all, tell user to run `/tg:start` first

2. **Read config.json**:
   - Read `output/{slug}/config.json`
   - Extract: topic, depth, examples, analogies, visual_emphasis

3. **Load scoping prompt** from `~/.claude/tg/prompts/scoping.md`

4. **Generate initial outline** following scoping prompt rules:
   - Scale chapter count to depth setting:
     - overview: 8-10 chapters
     - standard: 10-12 chapters
     - comprehensive: 12-14 chapters
   - Each chapter gets:
     - A descriptive title
     - 3-5 sections with 2-4 sub-topics each
     - 2-4 specific learning objectives
     - 4-8 key terms
     - 2-3 research queries optimized for Perplexity web search
   - Progression: foundational concepts → intermediate application → advanced topics
   - First chapter should always be introduction/overview
   - Last chapter should be synthesis/advanced topics/next steps

5. **Present outline to user** in a readable format:
   ```
   ## Proposed Outline: {title}

   **Chapter 1: {title}**
   - Sections: {section titles}
   - Key terms: {terms}

   **Chapter 2: {title}**
   ...
   ```

6. **Ask for feedback** via AskUserQuestion:
   - "How does this outline look?"
   - Options: "Looks good, proceed" / "I want to adjust some chapters" / "Too many/few chapters" / "Add/remove specific topics"

7. **Iterate** if user wants changes:
   - Apply their feedback
   - Show updated outline
   - Repeat until approved
   - Keep track of what they asked for so you don't lose changes between rounds

8. **Write outline.json** to `output/{slug}/outline.json`:
   Must match this exact schema:
   ```json
   {
     "title": "string",
     "description": "string",
     "chapters": [
       {
         "number": 1,
         "title": "string",
         "slug": "chapter-01-{short-name}",
         "learning_objectives": ["string"],
         "sections": [
           {
             "title": "string",
             "sub_topics": ["string"]
           }
         ],
         "key_terms": ["string"],
         "research_queries": ["string"]
       }
     ]
   }
   ```

   IMPORTANT:
   - `number` is 1-indexed sequential
   - `slug` is `chapter-{NN}-{short-name}` with zero-padded NN
   - `research_queries` should be specific, web-searchable queries — NOT vague topic names
     - Good: "What are the key differences between TCP and UDP for network engineers?"
     - Bad: "TCP vs UDP"

9. **Update config.json** — read, update `pipeline_stage` to `"scoped:true"`, write back

10. **Verify outline**:
    ```bash
    node "$HOME/.claude/tg/bin/sws-tools.cjs" outline-chapters output/{slug}
    ```

11. **Auto-invoke `/tg:research`** — IMMEDIATELY invoke via Skill tool. Do NOT just tell the user to run it.
</process>
