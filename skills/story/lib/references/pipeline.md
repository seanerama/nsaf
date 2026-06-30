# Story Maker Pipeline

## Stages

```
start → outline ─┬→ write ─────┬→ illustrate ─┐
                 └→ portraits ─┘               ├→ build
                               └→ narrate ─────┘
```

## Stage Sequence

| # | Stage | Command | Phase | Description |
|---|-------|---------|-------|-------------|
| 1 | Start | /story:start | Setup | Capture story idea, initialize project |
| 2 | Outline | /story:outline | Writing | Story arc, characters (age/gender/accent), scenes |
| 3 | Write | /story:write | Writing | Narration script with voice tags + illustration prompts |
| 4 | Portraits | /story:portraits | Production | One hero portrait per character (refs for illustrate) |
| 5 | Illustrate | /story:illustrate | Production | Scene illustrations (Nano Banana w/ refs, or Leonardo) |
| 6 | Narrate | /story:narrate | Production | Multi-voice audio (deterministic voice picks) |
| 7 | Build | /story:build | Assembly | Assemble MP4 video from images + audio |

## Dependencies

| Stage | Depends On | Can Parallel With |
|-------|-----------|-------------------|
| Start | — | — |
| Outline | Start | — |
| Write | Outline | Portraits |
| Portraits | Outline | Write |
| Illustrate | Write, Portraits | Narrate |
| Narrate | Write | Illustrate |
| Build | Illustrate, Narrate | — |

## Utility Commands

- `/story:status` — Show current pipeline state
- `/story:next` — Show/invoke next available stage
- `/story:help` — List all commands

## Provider Defaults (config.json)

- `image_provider`: `nano-banana` (Gemini Flash Image, character-portrait references)
  - Set to `leonardo` to skip portraits and use text-only Leonardo.
- `tts_provider`: `openai` (tts-1-hd, 6 fixed voices, deterministic mapping)
  - Set to `elevenlabs` for a 5000+ voice library indexed by attribute.
  - Voice picks are mechanical — see `~/.claude/story/bin/pick-voice.cjs`.
