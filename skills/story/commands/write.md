---
name: story:write
description: Write full narration script with voice tags and illustration prompts
allowed-tools:
  - Read
  - Write
  - Bash
  - Skill
  - Agent
---
<objective>
Read the outline and write the complete narration script with [VOICE:name] tags
for multi-voice TTS and detailed illustration prompts for each scene.

Produces: story-output/script.md
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
@~/.claude/story/references/style-guide.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage write`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage write
   ```

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage write
   ```

3. Read story-output/outline.md for story arc, characters, scenes, style guide.

4. For each scene in the outline, write:

   **Narration section:**
   - Full prose narration tagged with `[VOICE:narrator]`
   - Character dialogue tagged with `[VOICE:character-name]`
   - Character names in voice tags must exactly match the character reference sheet
   - Write vivid, age-appropriate prose (match the genre/tone from concept.md)
   - Include scene transitions (natural pauses between scenes)

   **Illustration prompt section:**
   - Detailed prompt for the configured image provider (Nano Banana by default,
     Leonardo as fallback).
   - Include the style guide preamble (art medium, palette, lighting).
   - Describe the specific **scene** — composition, action, setting, mood,
     camera framing. The `illustrate` stage will pass per-character portrait
     PNGs as reference images, so DO NOT re-describe every character's anatomy
     in every prompt. Refer to characters by name + one identifier
     (e.g. "Freddie in his blue jacket").
   - Specify "Aspect ratio 16:9" and quality descriptors.
   - Each prompt should be self-contained for SCENE content, but assume the
     reference portrait carries identity.

5. Write story-output/script.md with all scenes.

   Format per scene:
   ```markdown
   ## Scene N: [Title]

   ### Narration

   [VOICE:narrator]
   Prose text here...

   [VOICE:character-name]
   "Dialogue here."

   ### Illustration Prompt

   A [style] illustration of [scene description]...

   ---
   ```

6. Complete stage:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage write --output story-output/script.md
   ```

7. Check next stages:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" graph next
   ```
   Both illustrate and narrate should be available (parallel).
   Tell the user both are available and which you'll run first, then invoke `/story:illustrate`.
   After illustrate completes, invoke `/story:narrate` (or vice versa).
</process>
