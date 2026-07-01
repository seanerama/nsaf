---
description: Show Daily-Brief commands and current state
---

# /brief:help

Show the available Daily-Brief commands and the current state.

## Process
1. Run `brief status` and show the output (profiles, last runs).
2. List the commands below.

## Commands

| Command | What it does |
|---------|--------------|
| `/brief:run [profile]` | Sweep a profile's sources for the latest → brief (HTML + summary + podcast script). |
| `/brief:topic <topic> [profile] [sources]` | Research one topic → brief. Surfaces what's new since last look. |
| `/brief:setup [profile]` | Create or edit a profile (role/lens with topics + sources). |
| `/brief:status` | Show profiles, history counts, and last runs. |
| `/brief:help` | This help. |

## Notes
- Profiles live in `data/profiles/<slug>/` (reference.md, history.md, knowledge-base.md).
- Each run writes to `data/briefs/<slug>/<timestamp>/`.
- Open web research uses the Perplexity MCP (paid); the rest runs on your Claude subscription.
- See `sdd-output/project-plan.md` for architecture; `README.md` for install.
