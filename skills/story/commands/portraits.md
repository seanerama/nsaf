---
name: story:portraits
description: Generate one hero portrait per character via Nano Banana (used as reference images by the illustrate stage)
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Skill
  - Agent
---
<objective>
For every non-narrator character in the reference sheet, generate ONE canonical
1024×1024 portrait via Nano Banana (Gemini Flash Image). These are then passed
as reference images to every scene in `illustrate`, eliminating the
character-drift-across-scenes problem.

Produces: story-output/characters/<slug>.png  (one per character)
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
@~/.claude/story/references/style-guide.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage portraits`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage portraits
   ```
   Verify outline stage is complete.

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage portraits
   ```

3. Verify prerequisites:
   - `GEMINI_API_KEY` (or `NANOBANANA_GEMINI_API_KEY`) is set — check `.env`.
     If missing, ask the user before proceeding.
   - `gemini` CLI on PATH and nanobanana extension installed:
     `gemini extensions list | grep -q nanobanana || gemini extensions install https://github.com/gemini-cli-extensions/nanobanana`

4. Read story-output/outline.md and parse the Character Reference Sheet:
   - Skip the `Narrator` row (no portrait needed).
   - For each remaining row, read columns: Name, Age, Gender, Accent, Visual
     Description, Portrait Prompt.
   - Slugify Name → lowercase, ASCII, hyphenated (`Alden` → `alden`).

5. Ensure story-output/characters/ exists.

6. Skip already-generated portraits (resumability):
   - If `story-output/characters/<slug>.png` already exists and is non-empty, skip.

7. For each character that needs a portrait, build the final prompt:

   ```
   <style preamble from the story's Visual Style Guide section in outline.md>
   Portrait of <Name>: <Visual Description>.
   <Portrait Prompt from the reference sheet>.
   Plain neutral background, neutral expression, front-facing or three-quarter
   view, full-body or torso composition, soft even lighting. The character is
   the only subject. No text.
   ```

   Then call the helper:
   ```bash
   bash "$HOME/.claude/story/bin/nano-banana-image.sh" \
     "story-output/characters/<slug>.png" \
     "1:1" \
     "<final prompt above>"
   ```

   The helper:
   - Runs `gemini --yolo "/generate ..."` with `--aspect=1:1`.
   - Crops/pads the result to exact 1024×1024 via FFmpeg.
   - Writes to the given output path.

8. Verify every non-narrator character has a portrait PNG.

9. Complete stage:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage portraits --output story-output/characters/
   ```

10. Auto-continue — invoke `/story:next`. (The graph allows both write and
    illustrate downstream; write is the immediate next step.)
</process>

<notes>
- Portraits are *reference identity anchors*, NOT publishable art. Drift in
  pose/clothing across portrait runs doesn't matter as long as the face,
  hair, build, and signature clothing are stable. That stability is what every
  scene in `illustrate` will lock to.
- If a character has a strong "in-story" signature outfit (e.g. red sneakers,
  blue jacket), include it in the portrait so scene renders inherit it.
- Cost: ~$0.04 per portrait × ~3 characters = ~$0.12 per story.
- This stage runs once per story even if you re-run `illustrate` many times.
</notes>
