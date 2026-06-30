---
name: story:start
description: Begin a new illustrated audio story
argument-hint: "[story idea]"
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
   mkdir -p story-output/images story-output/audio
   ```

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
   - If arguments provided, use them as the initial idea
   - If no arguments, ask the user for their story idea
   - Ask minimal clarifying questions (or none if the idea is clear)
   - Extract or generate: title, genre, tone, target length, art style
   - If characters are mentioned, capture names and descriptions
   - Default art style to "watercolor storybook" unless the idea suggests otherwise
   - Read the style guide: `~/.claude/story/references/style-guide.md`

9. Write story-output/concept.md with all extracted information.

10. Complete stage and auto-continue:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage start --output story-output/concept.md
    ```
    Then immediately invoke `/story:outline` — do NOT just tell the user to run it.
</process>
