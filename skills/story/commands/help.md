---
name: story:help
description: Show all Story Maker commands and pipeline overview
allowed-tools:
  - Read
  - Bash
---
<objective>
Display all available /story:* commands and the pipeline overview.
</objective>

<process>
1. Display the command list:

   **Story Maker — AI-Orchestrated Illustrated Audio Stories**

   **Pipeline Commands** (run in order):
   | Command | Description |
   |---------|-------------|
   | `/story:start` | Begin a new story — capture your idea |
   | `/story:outline` | Build story arc, characters (age/gender/accent), scenes |
   | `/story:write` | Write narration script + illustration prompts |
   | `/story:portraits` | Generate hero portrait per character (refs for illustrate) |
   | `/story:illustrate` | Generate scene images (Nano Banana w/ character refs, or Leonardo) |
   | `/story:narrate` | Generate multi-voice audio via TTS (deterministic voice picks) |
   | `/story:build` | Assemble final MP4 video |

   **Utility Commands**:
   | Command | Description |
   |---------|-------------|
   | `/story:status` | Show pipeline progress |
   | `/story:next` | Show/invoke next stage |
   | `/story:help` | This help message |

   **Pipeline Flow**:
   ```
   start → outline ─┬→ write ─────┬→ illustrate ─┐
                    └→ portraits ─┘               ├→ build → final.mp4
                                  └→ narrate ─────┘
   ```

2. If STATE.md exists, also show current progress:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" graph status
   ```
</process>
