---
name: story:status
description: Show current story pipeline state and progress
allowed-tools:
  - Read
  - Bash
---
<objective>
Display the current state of the story pipeline — completed stages, active stages,
and what's next.
</objective>

<process>
1. Load pipeline status:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" graph status
   ```

2. Display a formatted summary:
   - Progress bar with percentage
   - List completed stages with their outputs
   - Show active stages
   - Show available next stages
   - Show waiting stages with their missing dependencies

3. If no STATE.md exists, inform the user to run `/story:start`.
</process>
