---
name: tg:status
description: Show pipeline progress for all topics
allowed-tools:
  - Read
  - Bash
  - Glob
---
<objective>
Check all topic directories under output/ and display pipeline progress for each.
</objective>

<context>
```bash
node "$HOME/.claude/tg/bin/sws-tools.cjs" status
```
</context>

<process>
1. **Run status check**:
   ```bash
   node "$HOME/.claude/tg/bin/sws-tools.cjs" status
   ```

2. **Parse the JSON output** and display a readable summary for each topic:

   For each topic, show a checklist:
   ```
   ## {Topic Name} ({slug})

   - [x] Started (config.json)
   - [x] Scoped (outline.json) — {N} chapters
   - [x] Researched — {N}/{total} chapters
   - [ ] Written — {N}/{total} chapters
   - [ ] Diagrams added
   - [ ] Study guides — {N}/{total} chapters
   - [ ] Slides
   - [ ] Podcast prompt
   - [ ] Review report
   ```

3. If no topics found, display:
   ```
   No topics found. Run /tg:start to begin a new learning pipeline.
   ```
</process>
