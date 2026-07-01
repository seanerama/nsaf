# Story Maker Pipeline

## Stages

```
start → outline ─┬→ write ─────┬→ illustrate ─┬→ build (MP4)
                 └→ portraits ─┘               ├→ pdf   (print book)
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
| 8 | PDF | /story:pdf | Assembly | Assemble a print-ready 8.5×8.5 PDF picture book |

## Dependencies

| Stage | Depends On | Can Parallel With |
|-------|-----------|-------------------|
| Start | — | — |
| Outline | Start | — |
| Write | Outline | Portraits |
| Portraits | Outline | Write |
| Illustrate | Write, Portraits | Narrate |
| Narrate | Write | Illustrate |
| Build | Illustrate, Narrate | PDF |
| PDF | Write, Illustrate | Narrate, Build |

Note: PDF and Build are BOTH leaf stages — you can generate either or both.
PDF doesn't need audio (it's a printed book, not a video).

## Utility Commands

- `/story:status` — Show current pipeline state
- `/story:next` — Show/invoke next available stage
- `/story:help` — List all commands

## Provider Defaults (config.json)

- `image_provider`: `nano-banana` (Gemini Flash Image, character-portrait references)
  - Set to `leonardo` to skip portraits and use text-only Leonardo.
- `tts_provider`: `elevenlabs` (5000+ voice library indexed by attribute)
  - Set to `openai` for the 6 fixed voices with deterministic mapping.
  - Voice picks are mechanical — see `~/.claude/story/bin/pick-voice.cjs`.
