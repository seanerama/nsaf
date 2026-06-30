# Next Action Workflow

Determines and invokes the next available pipeline stage.

## Steps

1. **Load pipeline state**:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" graph next
   ```

2. **Interpret results**:
   - If empty array → Pipeline is complete. Show summary of all outputs.
   - If single stage → Immediately invoke it via `/story:<command>`
   - If multiple stages (parallel) → Report which are available, ask user preference, then invoke

3. **Display format** (when showing options):
   ```
   Next available stages:
   - /story:illustrate — Generate scene illustrations (can run in parallel)
   - /story:narrate — Generate multi-voice audio (can run in parallel)

   Which would you like to start first? (Or I can run them sequentially)
   ```

4. **Always auto-invoke** — never leave the user with a "run X" instruction.
