---
name: story:next
description: Show and invoke the next available pipeline stage
allowed-tools:
  - Read
  - Bash
  - Skill
---
<objective>
Determine the next available stage(s) in the pipeline and invoke them.
</objective>

<execution_context>
@~/.claude/story/workflows/next-action.md
</execution_context>

<process>
1. Load next stages:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" graph next
   ```

2. Interpret results:
   - If empty → Pipeline is complete. Read story-output/STATE.md and show a summary of all outputs.
   - If single stage → Immediately invoke it via `/story:<command>` (use the Skill tool).
   - If multiple stages (parallel) → Tell the user which are available and ask which to start first, then invoke the chosen one.

3. IMPORTANT: Always auto-invoke. Never leave the user with a "run X" instruction.
</process>
