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
For every non-narrator character in the reference sheet, produce ONE canonical
1024×1024 portrait that the `illustrate` stage will pass to Nano Banana as a
reference for scene renders. Portraits come from ONE of three sources per
character, in priority order:

1. A **user-provided photo** matching the character's slug in
   `story-output/characters-source/` (per-story) or
   `~/nsaf/data/story/characters/` (reusable central library) — for real
   people, pets, or specific characters the user wants to anchor exactly.
2. An **explicit absolute path** in the character reference sheet's
   `Photo Path` column — for ad-hoc photos anywhere on disk.
3. **AI-generated via Nano Banana** from the reference sheet's visual
   description + portrait prompt — for fantasy/original characters.

Mixed casts work: a real-photo kid alongside an AI-generated dragon.

Produces: story-output/characters/<slug>.png  (one per character, 1024×1024)
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

3. Load env + verify prerequisites:
   ```bash
   source "$HOME/.claude/story/bin/load-nsaf-env.sh"
   ```
   That's the safe env parser — line-by-line, no shell eval, immune to
   unquoted `|` values that used to abort the pipeline (STORY-MAKER-ISSUES.md #4).

   Then verify:
   - Any of `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `NANOBANANA_API_KEY` is
     set (the image helper accepts all three in that precedence order —
     see STORY-MAKER-ISSUES.md #3). If none, ask the user to add
     `GEMINI_API_KEY` to `~/nsaf/.env`.
   - `python3` and `ffmpeg` on PATH.

   NOTE: We no longer require the `gemini` CLI or its nanobanana
   extension. The image helper calls Gemini's REST API directly
   (STORY-MAKER-ISSUES.md #1).

4. Read story-output/outline.md and parse the Character Reference Sheet:
   - Skip the `Narrator` row (no portrait needed).
   - For each remaining row, read columns: Name, Age, Gender, Accent, Visual
     Description, Portrait Prompt, Photo Path (optional).
   - Slugify Name → lowercase, ASCII, hyphenated (`Alden` → `alden`).

5. Ensure story-output/characters/ exists.

6. Skip already-generated portraits (resumability):
   - If `story-output/characters/<slug>.png` already exists and is non-empty, skip.

7. **For each character that needs a portrait, resolve the source in priority
   order** (first hit wins):

   a. **Per-story photo:** any of
      `story-output/characters-source/<slug>.{png,jpg,jpeg,webp,heic}`.
      (Case-insensitive extension match.)

   b. **Central library photo:** any of
      `~/nsaf/data/story/characters/<slug>.{png,jpg,jpeg,webp,heic}`.
      Useful for recurring characters (own kids, own pets) across many stories.

   c. **Explicit Photo Path from the reference sheet:** if the row's
      `Photo Path` column contains an absolute path AND the file exists.

   d. **AI-generate** via Nano Banana.

   For sources (a)/(b)/(c), normalize the photo to a 1024×1024 portrait:
   ```bash
   bash "$HOME/.claude/story/bin/photo-to-portrait.sh" \
     "<source photo path>" \
     "story-output/characters/<slug>.png"
   ```
   Log: `"Using user photo for <Name>: <source path>"`.

   The `photo-to-portrait.sh` helper is pure ffmpeg — no env needed.

   For source (d), build the final prompt:
   ```
   <style preamble from the story's Visual Style Guide section in outline.md>
   Portrait of <Name>: <Visual Description>.
   <Portrait Prompt from the reference sheet>.
   Plain neutral background, neutral expression, front-facing or three-quarter
   view, full-body or torso composition, soft even lighting. The character is
   the only subject. No text.
   ```
   Then call the AI helper (direct REST — bypasses the flaky gemini CLI +
   nanobanana extension chain, see STORY-MAKER-ISSUES.md #1):
   ```bash
   python3 "$HOME/.claude/story/bin/nano-banana-image.py" \
     "story-output/characters/<slug>.png" \
     "1:1" \
     "<final prompt above>"
   ```
   The helper:
   - Auto-sources `~/nsaf/.env`, accepts any of `GEMINI_API_KEY`,
     `GOOGLE_API_KEY`, or `NANOBANANA_API_KEY`.
   - Defaults to `gemini-2.5-flash-image` (flash — fast + available).
     Override via `NANOBANANA_MODEL`; if that's pinned to a pro model and
     the pro model 503s, the helper auto-falls-back to flash.
   - Classifies errors: 429 (quota) exits immediately, 500/503 (transient)
     retries with backoff. No more retrying-a-quota-error-for-an-hour.
   Log: `"Generated portrait for <Name> via Nano Banana"`.

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
- Cost: ~$0.04 per portrait × ~3 AI-generated characters ≈ $0.12/story.
  User photos cost $0 and give the best identity lock.
- This stage runs once per story even if you re-run `illustrate` many times.

**Photo tips for user-supplied refs:**
- Front-facing or three-quarter view works best. Full profile shots are the
  worst — Nano Banana can't easily extrapolate the other 3/4 of the face.
- One subject per photo. Group shots confuse the model about which person is
  the character.
- Reasonable lighting (not backlit silhouette). The photo doesn't need to be
  studio-quality — a decent phone snap works.
- For pets: side-view or three-quarter, well-lit, whole animal visible.
- The photo is cropped square, so anything at the edges gets cut. Center the
  subject.
- File name must match the character's slug: `Alden` → `alden.jpg`,
  `Freddie the Cat` → `freddie-the-cat.png`.
</notes>
