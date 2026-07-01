---
description: Show Daily-Brief profiles, history counts, and last runs
---

# /brief:status

Show the current Daily-Brief state.

## Process
1. Run `brief status` and present the output: each profile's topic count, history size, and
   most recent run (timestamp + item counts), followed by overall totals.
2. If there are no profiles, point the user to `/brief:setup`.
3. Optionally surface the most recent run dir so the user can open its `brief.html`.
