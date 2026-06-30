---
name: story:illustrate
description: Generate scene illustrations via Nano Banana (with character portraits) or Leonardo AI
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
  - mcp__leonardo-ai__high_definition_generalist
  - mcp__leonardo-ai__hyperrealistic
  - mcp__leonardo-ai__accurate_text_rendering
---
<objective>
Generate one illustration per scene. Default provider is **Nano Banana**
(Gemini Flash Image) with the per-character portraits from `story-output/characters/`
passed in as reference images, so characters stay on-model across every scene.
Leonardo remains the fallback.

Produces: story-output/images/scene-01.png through scene-NN.png (1920×1080)
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
@~/.claude/story/references/style-guide.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage illustrate`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage illustrate
   ```

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage illustrate
   ```

3. Read inputs:
   - story-output/script.md — illustration prompt + characters present per scene.
   - story-output/outline.md — Visual Style Guide + Character Reference Sheet.
   - story-output/characters/ — per-character portrait PNGs.

4. Read config:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" config get resolution
   node "$HOME/.claude/story/bin/story-tools.cjs" config get image_provider
   ```
   `image_provider` defaults to `nano-banana`. Other accepted values:
   `leonardo` (legacy text-only path).

5. Ensure story-output/images/ exists. Skip scenes that already have a non-empty
   PNG (resumability).

6. **Provider = nano-banana (default):**

   For each scene NN that needs an image:

   a. Parse the scene block in script.md. From the scene's `**Characters**` line
      (or the matching outline scene row), identify which named characters are
      present. Map each → `story-output/characters/<slug>.png`. Skip the
      Narrator. If a character's portrait file is missing, log a warning and
      treat them as absent for reference purposes (the prompt still mentions
      them; they just won't be identity-anchored).

   b. Take the scene's `### Illustration Prompt` block from script.md.

   c. Call the helper:
      ```bash
      bash "$HOME/.claude/story/bin/nano-banana-image.sh" \
        "story-output/images/scene-NN.png" \
        "16:9" \
        "<scene illustration prompt>" \
        story-output/characters/<char1>.png \
        story-output/characters/<char2>.png
      ```
      The helper passes refs to `gemini --yolo "/edit ref1 ref2 ... '<compose prompt>'"`
      and crops/pads the result to exactly 1920×1080 via FFmpeg.

   d. Cap reference inputs at 5 portraits per scene (Gemini Flash Image limit).
      If the scene names >5 characters, prefer the ones with dialogue in this
      scene, then prominence.

   e. If the helper exits non-zero (gemini missing, quota, etc.), fall through to
      provider = leonardo for that scene and log which scenes fell back.

   f. Log progress: "Generated scene N of M via nano-banana (refs: alden, freddie)".

7. **Provider = leonardo (legacy fallback / explicit override):**

   For each scene NN that needs an image:
   a. Take the illustration prompt from script.md.
   b. Prepend the style guide preamble from outline.md.
   c. Call `mcp__leonardo-ai__high_definition_generalist` at 1920×1080.
   d. Save to story-output/images/scene-NN.png.

8. Optionally generate a title card image (scene-00.png or title.png).

9. Verify all scene images exist and are 1920×1080.

10. Complete stage:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage illustrate --output story-output/images/
    ```

11. Check next and auto-continue:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" graph next
    ```
    If narrate is still pending → invoke `/story:narrate`
    If narrate is complete → invoke `/story:build`
</process>

<notes>
- **Why portraits + refs instead of text-only:** Leonardo / SDXL with text-only
  prompts cannot lock identity across N stateless calls — small wording shifts
  produce visible face drift. Conditioning each scene on the same per-character
  reference PNG (Nano Banana / Gemini Flash Image, up to 5 refs per call) is
  the 2025-era fix recommended in the audio & image research report.
- **Cost delta:** ~$0.04 per scene × 10 scenes ≈ $0.40 per story for nano-banana,
  plus ~$0.12 in portraits — well under the 10× ceiling.
- **No-character scenes** (pure landscape, abstract title cards) can be sent
  via the leonardo path; pass refs only when at least one named character is in
  the scene.
- **Stay on Leonardo intentionally:** set `image_provider=leonardo` in config.
</notes>
