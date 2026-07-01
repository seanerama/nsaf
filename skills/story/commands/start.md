---
name: story:start
description: Begin a new illustrated audio story
argument-hint: "[story idea text | path to idea .md file]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
  - Skill
  - Agent
---
<objective>
Initialize a new story project. Capture the user's idea, create story-output/,
and produce concept.md.

Produces: story-output/concept.md
</objective>

<execution_context>
@~/.claude/story/workflows/start.md
@~/.claude/story/workflows/run-stage.md
@~/.claude/story/references/pipeline.md
@~/.claude/story/references/style-guide.md
</execution_context>

<context>
Arguments: {{args}}

Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init start`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init start
   ```

2. If STATE.md exists and has progress:
   - Show current state summary
   - Ask: "Resume existing story or start fresh?"
   - If resume → invoke `/story:next`
   - If fresh → confirm overwrite, then continue

3. Create story-output/ directory structure:
   ```bash
   mkdir -p story-output/images story-output/audio story-output/characters-source
   ```

   The `characters-source/` dir is where the user drops photos to use as
   character identity anchors (real people, pets). Named by character slug:
   `alden.jpg`, `mocha-the-dog.png`, etc. Any FFmpeg-decodable format works.
   See step 8 below for the user-facing prompt.

4. Initialize STATE.md from template (story/templates/state.md) with current timestamp.

5. Initialize config.json:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" config ensure
   ```

6. Update .gitignore — add story-output/ and .env if not present.

7. Mark start stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage start
   ```

8. Capture the user's story idea:
   - **If arguments provided, resolve idea source:**
     - Check whether the argument is a path to a readable file:
       ```bash
       ARG="{{args}}"
       # Expand ~ if present
       ARG="${ARG/#\~/$HOME}"
       [ -f "$ARG" ] && [ -r "$ARG" ] && echo "file"
       ```
       If it's a readable file: use the Read tool to load the file's contents
       as the story idea. Record the source path in concept.md's frontmatter
       (add `idea_source: <absolute path>`) for provenance so a later re-read
       is possible.
     - Otherwise: treat the argument text as the idea directly (short idea
       inline).
   - **If no arguments**, ask the user for their story idea.
   - Ask minimal clarifying questions (or none if the idea is clear and detailed —
     e.g. a full plot in a referenced .md file usually needs no clarifying pass).
   - Extract or generate: title, genre, tone, target length, art style.
   - If the source has detailed plot beats, preserve them verbatim in
     concept.md; do NOT paraphrase away specificity the author put in.
   - If characters are mentioned, capture names and descriptions.
   - Default art style to "watercolor storybook" unless the idea suggests otherwise.
   - Read the style guide: `~/.claude/story/references/style-guide.md`

   **If any character is based on a real person or pet**, tell the user
   how to provide reference photos:

   > Drop reference photos for real-people/pet characters at
   > `story-output/characters-source/<name>.<ext>` before running
   > `/story:portraits` (accepted: png, jpg, jpeg, webp, heic). Name each
   > file by the character's slug — e.g., `Alden` → `alden.jpg`,
   > `Mocha the Dog` → `mocha-the-dog.png`.
   >
   > For characters you re-use across many stories, put photos at
   > `~/nsaf/data/story/characters/<slug>.<ext>` instead — the pipeline
   > checks there too.
   >
   > For any character without a photo, the pipeline AI-generates a
   > portrait from the Visual Description in the outline. Mixed casts
   > (real-photo kid, AI-generated dragon) work naturally.

9. Write story-output/concept.md with all extracted information.

10. Complete stage and auto-continue:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage start --output story-output/concept.md
    ```
    Then immediately invoke `/story:outline` — do NOT just tell the user to run it.
</process>
