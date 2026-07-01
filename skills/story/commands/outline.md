---
name: story:outline
description: Build story arc, characters, scenes, and voice assignments
allowed-tools:
  - Read
  - Write
  - Bash
  - Skill
  - Agent
---
<objective>
Read the concept document and build a complete story outline with arc, characters,
scene breakdown, visual style guide, and voice assignments.

Produces: story-output/outline.md
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
@~/.claude/story/references/pipeline.md
@~/.claude/story/references/style-guide.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage outline`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage outline
   ```
   Verify start stage is complete.

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage outline
   ```

3. Read story-output/concept.md for the story idea, characters, and settings.

4. Read the style guide: `~/.claude/story/references/style-guide.md`

5. Build the story outline:
   - **Story arc**: beginning, rising action, climax, resolution
   - **Visual style guide**: medium, palette, lighting, consistent elements
     (based on concept.md art style + style-guide.md reference)
   - **Character reference sheet**: a markdown table with these columns, one row
     per character (including a `Narrator` row):

     | Name | Age | Gender | Accent | Visual Description | Portrait Prompt | Photo Path | Voice ID | Voice Description |

     Column rules:
     - **Age**: integer years for kids ("7"), or category for adults/non-human
       ("adult", "elder", "young-adult", "teen"). Required — drives both portrait
       generation and voice picking. For Narrator use "—".
     - **Gender**: `male` | `female` | `nonbinary` | `—` (Narrator).
     - **Accent**: short label, e.g. `neutral-us`, `british-rp`, `southern-us`,
       `irish`, `—`. Required.
     - **Visual Description**: detailed, immutable identity features — face
       shape, eye/hair color, build, signature clothing, distinguishing marks.
       This is the SOURCE OF TRUTH that downstream stages will repeat verbatim.
       Narrator: `—`.
     - **Portrait Prompt**: a self-contained 1–3 sentence prompt suitable for
       generating a single front-facing reference portrait (used by the
       `portraits` stage). MUST start with the style preamble for the story,
       describe the character standing in a neutral plain background, neutral
       expression, full body or three-quarter view. Narrator: `—`. Ignored if
       a user photo is provided (see below).
     - **Photo Path**: `—` (default) OR an absolute path to a user-provided
       photo. If set and the file exists, the `portraits` stage uses THAT photo
       (cropped to 1024) as the character's identity anchor instead of AI-
       generating one from the portrait prompt. Also honored automatically if
       a photo is dropped at `story-output/characters-source/<slug>.<ext>`
       (per-story) or `~/nsaf/data/story/characters/<slug>.<ext>` (reusable
       library) — those convention paths win over Photo Path if both exist.
       For fantasy or original characters where you want AI-generated art,
       leave this `—`.
     - **Voice ID**: leave blank `—` — the `narrate` stage assigns this
       deterministically from `(Age, Gender, Accent)` against the configured TTS
       provider's voice library. Do NOT pick from the OpenAI 6 here; that choice
       is now mechanized, not vibes-based.
     - **Voice Description**: short prose hint to the voice picker
       (e.g. "energetic, curious", "calm, grandfatherly"). Optional but useful
       as a tiebreaker.

   - **Scenes** (8-12 for picture books, more for longer stories):
     Each scene gets: title, setting, characters present, action, key dialogue
     beats, illustration focus, mood.

6. Write story-output/outline.md with all sections.

7. Complete stage:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage outline --output story-output/outline.md
   ```

8. Auto-continue — immediately invoke `/story:write`.
</process>
