# Start Workflow

Initializes story-output/ for a new story.

## Steps

1. **Create directory structure**:
   ```
   story-output/
   ├── STATE.md
   ├── config.json
   ├── images/
   └── audio/
   ```

2. **Initialize STATE.md** from template with current timestamp

3. **Initialize config.json** from defaults:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" config ensure
   ```

4. **Update .gitignore**:
   - Add `story-output/` if not already present
   - Add `.env` if not already present

5. **Capture the user's idea**:
   - Ask for their story idea (or use what they already provided)
   - Extract: title, genre, tone, characters, setting, art style
   - Default art style to "watercolor storybook" unless the idea suggests otherwise
   - Write concept.md

6. **Mark start stage complete and auto-continue**:
   - Complete the start stage
   - Immediately invoke `/story:outline`
