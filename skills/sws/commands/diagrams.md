---
name: sws:diagrams
description: Add mermaid diagrams to textbook chapters (parallel sub-agents)
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Agent
  - Skill
---
<objective>
Diagram insertion pass: spawn parallel sub-agents that each read a chapter,
identify concepts needing visualization, and insert mermaid diagram blocks.
Updates chapters in place and regenerates textbook.md.

Produces: updated chapters/chapter-{nn}.md (with mermaid blocks), updated textbook.md
</objective>

<execution_context>
@~/.claude/sws/prompts/diagrams.md
@~/.claude/sws/references/pipeline-stages.md
</execution_context>

<context>
```bash
node "$HOME/.claude/sws/bin/sws-tools.cjs" active-topic
node "$HOME/.claude/sws/bin/sws-tools.cjs" outline-chapters <topic-dir>
```
</context>

<process>
1. **Find active topic** and verify pipeline_stage is "written:true"

2. **Read outline.json** for chapter list

3. **Spawn parallel diagram sub-agents** via Agent tool:
   - One Agent per chapter (multiple Agent calls in a single message)
   - Each agent gets this prompt:

   ```
   You are a technical diagram specialist for the StudyWS learning pipeline.

   TASK: Add mermaid diagrams to Chapter {N}: "{title}"

   Read the chapter file at: {topic_dir}/chapters/chapter-{nn}.md

   Then identify 2-6 concepts that benefit from visual representation and insert
   mermaid diagram blocks at appropriate points.

   DIAGRAM TYPE SELECTION GUIDE:
   - Process/workflow with steps → flowchart TD or flowchart LR
   - Request/response or actor interactions → sequenceDiagram
   - Hierarchy, taxonomy, or tree structure → graph TD
   - Timeline or chronological events → timeline
   - Entity relationships or data models → erDiagram
   - Class structures or interfaces → classDiagram
   - State transitions → stateDiagram-v2
   - Comparison of options → Use a markdown table instead (not mermaid)

   INSERTION RULES:
   - Place each diagram IMMEDIATELY AFTER the paragraph that explains the concept
   - Add a bold label above each diagram:
     **Figure {chapter_number}.{diagram_number}: {Short description}**
   - Minimum 2 diagrams, maximum 6 per chapter
   - Keep diagrams focused — one concept per diagram
   - Use clear, readable node labels (not abbreviations)
   - For flowcharts: use descriptive text in nodes, not single letters
   - Ensure mermaid syntax is valid (test by mentally parsing it)

   MERMAID SYNTAX REMINDERS:
   - Flowchart nodes: A[Text] for rectangles, B{Text} for diamonds, C((Text)) for circles
   - Arrows: --> for solid, -.-> for dotted, ==> for thick
   - Sequence diagram: participant names, arrows with ->> or -->>
   - Always use quotes around labels with special characters

   CRITICAL:
   - Do NOT modify any existing text — only INSERT diagram blocks
   - Do NOT remove or rephrase any content
   - Do NOT change heading levels or structure
   - The only additions should be the **Figure** label line and the ```mermaid block

   Write the updated chapter back to the SAME file:
   {topic_dir}/chapters/chapter-{nn}.md
   ```

4. **Wait for all sub-agents to complete**

5. **Regenerate textbook.md**:
   - Read outline.json for title and description
   - Read all updated chapter files in order
   - Rebuild TOC and concatenate
   - Write updated textbook.md

6. **Update config.json** — set pipeline_stage to "diagrams:true"

7. **Report**: "Added diagrams to {N} chapters. Textbook.md regenerated."

8. **Auto-invoke `/sws:guide`** — IMMEDIATELY invoke via Skill tool.
</process>
