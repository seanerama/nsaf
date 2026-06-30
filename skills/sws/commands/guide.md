---
name: sws:guide
description: Generate interactive HTML study guides with quizzes (parallel sub-agents)
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Agent
  - Skill
---
<objective>
Study guide generation: spawn parallel sub-agents that each create a self-contained
interactive HTML study guide for one chapter, with pre/post quizzes, key points,
mermaid diagrams, and animation scaffolding.

Produces: output/{topic-slug}/guides/chapter-{nn}.html (one per chapter)
</objective>

<execution_context>
@~/.claude/sws/prompts/guide-gen.md
@~/.claude/sws/templates/study-guide-base.html
@~/.claude/sws/templates/quiz-schema.json
@~/.claude/sws/references/pipeline-stages.md
</execution_context>

<context>
```bash
node "$HOME/.claude/sws/bin/sws-tools.cjs" active-topic
node "$HOME/.claude/sws/bin/sws-tools.cjs" outline-chapters <topic-dir>
```
</context>

<process>
1. **Find active topic** and verify pipeline_stage is "diagrams:true" (or at least "written:true")

2. **Read outline.json**, **config.json**, and the **study-guide-base.html template**

3. **Check for existing guide files** — skip chapters whose `guides/chapter-{nn}.html` exists

4. **Spawn parallel guide sub-agents** via Agent tool:
   - One Agent per un-generated chapter guide
   - Each agent gets this prompt:

   ```
   You are an interactive study guide generator for the StudyWS pipeline.

   TASK: Create an interactive HTML study guide for Chapter {N}: "{title}"

   Read these files for context:
   - Chapter content: {topic_dir}/chapters/chapter-{nn}.md
   - HTML template: ~/.claude/sws/templates/study-guide-base.html
   - Quiz schema: ~/.claude/sws/templates/quiz-schema.json

   CHAPTER STRUCTURE (from outline):
   Sections:
   {for each section: title + sub_topics}

   QUIZ STRUCTURE RULES:
   - Each section should be partitioned into halves or thirds (depending on sub-topic count)
   - Generate 5 quiz questions per partition
   - Total questions per chapter: 10-15
   - Questions test UNDERSTANDING, not rote memorization
   - Each question has exactly 4 options
   - Each question needs:
     - explanation: why the correct answer is correct
     - wrong_explanations: why each wrong answer is wrong (specific, instructive)
   - Pre-quiz and post-quiz use the SAME questions
   - Answers are HIDDEN until the user clicks "Reveal Answers"

   HTML STRUCTURE:
   Build a complete, self-contained HTML file using the base template's styles.
   The structure for each section partition should be:

   <div class="sws-quiz" data-section="{section-slug}" data-type="pre">
     <div class="sws-quiz-header">Pre-Quiz: {Section Name}</div>
     {for each question:}
     <div class="sws-quiz-question" data-question-id="{id}">
       <p>{question text}</p>
       <div class="sws-quiz-option" data-index="0">{option A}</div>
       <div class="sws-quiz-option" data-index="1">{option B}</div>
       <div class="sws-quiz-option" data-index="2">{option C}</div>
       <div class="sws-quiz-option" data-index="3">{option D}</div>
     </div>
   </div>

   <div class="section-content">
     <h2>{Section Title}</h2>
     <div class="sws-key-points">
       <h4>Key Points</h4>
       <ul>
         <li>{3-5 key points from this section}</li>
       </ul>
     </div>
     {content: important concepts, tables, explanations}
     {mermaid diagrams from the chapter — embed directly as <div class="mermaid">}
     <div class="sws-animation-slot" data-type="{type}" data-context="{description}">
       <p class="placeholder">Visual animation — coming soon</p>
     </div>
   </div>

   <div class="sws-quiz" data-section="{section-slug}" data-type="post">
     <div class="sws-quiz-header">Post-Quiz: {Section Name}</div>
     {same questions as pre-quiz}
   </div>

   QUIZ JSON:
   Embed questions as a JavaScript object in a <script> tag:
   ```javascript
   const questions = {
     "{section-slug}": [
       {
         "id": "{section-slug}-q1",
         "question": "...",
         "options": ["A", "B", "C", "D"],
         "correct": 0,
         "explanation": "...",
         "wrong_explanations": {"1": "...", "2": "...", "3": "..."}
       }
     ]
   };
   ```

   ANIMATION SLOTS:
   Place 1-3 animation placeholder divs per chapter where dynamic visualization would help:
   - data-type options: "process-flow", "state-change", "comparison", "timeline", "buildup"
   - data-context: brief description of what animation would show

   MERMAID DIAGRAMS:
   Convert any ```mermaid blocks from the chapter markdown into:
   <div class="mermaid">
   {mermaid code without the backtick fences}
   </div>

   KEY POINTS:
   - Extract 3-5 most important takeaways per section
   - Use bullet points, not paragraphs
   - These should be study-card quality — concise and memorable

   IMPORTANT:
   - Include ALL CSS from the base template inline in <style>
   - Include the full quiz engine JavaScript from the base template in <script>
   - The ONLY external dependency is the mermaid CDN script tag
   - The file must work when opened directly in a browser — no server needed
   - Replace {{CHAPTER_TITLE}}, {{LEARNING_OBJECTIVES}}, {{CONTENT}}, and {{QUESTIONS_JSON}}
     template variables with actual content

   Write the file to: {topic_dir}/guides/chapter-{nn}.html
   ```

5. **Wait for all sub-agents to complete**

6. **Verify all guide files exist**:
   ```bash
   node "$HOME/.claude/sws/bin/sws-tools.cjs" status {slug}
   ```

7. **Spot-check one guide** — Read the first guide file and verify:
   - It has `<!DOCTYPE html>` at the start
   - It contains `class="sws-quiz"` elements
   - It contains `const questions =` in a script block
   - It contains `class="mermaid"` divs (if chapter had diagrams)

8. **Update config.json** — set pipeline_stage to "guides:true"

9. **Report**: "Generated {N} interactive study guides in guides/"

10. **Auto-invoke `/sws:slides`** — IMMEDIATELY invoke via Skill tool.
</process>
