---
name: story:narrate
description: Generate multi-voice audio narration via TTS
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
---
<objective>
Parse the script for voice tags, generate TTS audio for each voice segment,
and assemble per-scene audio files with multi-voice narration.

Produces: story-output/audio/scene-01.mp3 through scene-NN.mp3
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage narrate`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage narrate
   ```

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage narrate
   ```

3. Read story-output/script.md — parse narration sections with [VOICE:name] tags.
4. Read story-output/outline.md — get the Character Reference Sheet. Each row
   has Name, Age, Gender, Accent, (Visual Description), (Portrait Prompt),
   Voice ID, Voice Description.
5. Read config for TTS settings:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" config get tts_provider
   node "$HOME/.claude/story/bin/story-tools.cjs" config get tts_model
   ```

6. **Resolve every character's Voice ID deterministically (NOT by LLM vibes).**

   For each row in the Character Reference Sheet whose Voice ID column is
   blank/`—`, run:
   ```bash
   node "$HOME/.claude/story/bin/pick-voice.cjs" \
     "<tts_provider>" "<Age>" "<Gender>" "<Accent>" "<Voice Description>"
   ```
   The script returns one of:
   - A concrete voice ID (e.g. `echo`, `nova`, or a 20-char ElevenLabs ID).
   - `SEARCH:<query>` — only happens for ElevenLabs when the user hasn't
     supplied `~/.claude/story/elevenlabs-voices.json`. In that case, run a
     `GET https://api.elevenlabs.io/v2/voices?search=<query>&voice_type=premade`
     call and take the top result's `voice_id`.

   Write the resolved Voice ID back into outline.md's reference sheet so
   subsequent runs are stable, and cache the picks in
   `story-output/voice-assignments.json` (`{ "<name>": "<voice_id>" }`).

   This replaces the prior LLM-picks-from-six-voices step that produced
   inappropriate matches (e.g. British-woman voice for a young boy).

7. Verify OPENAI_API_KEY is available:
   - Check .env file in project root
   - If not found, ask the user to provide it.
   - If `tts_provider=elevenlabs`, also require `ELEVENLABS_API_KEY`.

8. Ensure story-output/audio/ directory exists.

9. Check for already-generated audio (for resumability):
   - List existing files in story-output/audio/
   - Skip scenes that already have audio.

10. For each scene that needs audio:
    a. Parse the [VOICE:name] tags to extract text segments per voice.
    b. For each voice segment:
      - Look up the voice ID from voice-assignments.json (or reference sheet).
      - Call the TTS API.
        - **openai/tts-1-hd (default):**
          ```bash
          curl -s https://api.openai.com/v1/audio/speech \
            -H "Authorization: Bearer $OPENAI_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"model":"tts-1-hd","input":"...","voice":"<resolved voice id>"}' \
            --output segment.mp3
          ```
        - **elevenlabs:**
          ```bash
          curl -s "https://api.elevenlabs.io/v1/text-to-speech/<voice_id>?output_format=mp3_22050_32" \
            -H "xi-api-key: $ELEVENLABS_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"text":"...","model_id":"eleven_multilingual_v2"}' \
            --output segment.mp3
          ```
          NOTE: ElevenLabs returns 22050 Hz mono MP3 by default; match the
          `-ar` in the concat filter below to 22050 when this provider is
          active. The concat filter rebuilds frame boundaries so a mid-pipeline
          sample-rate switch is fine — just keep all segments WITHIN one scene
          at the same rate.
      - Save as temp file: story-output/audio/segments/scene-NN-seg-MM.mp3
   c. Concatenate segments with brief silence (0.3s) between speakers using FFmpeg's
      **concat filter** — NOT the `concat:` protocol with `-c copy`.

      WHY: byte-concatenating MP3s with `-c copy` keeps each segment's encoder
      delay/padding, leaving a click/gap at every join (audible as "choppy" audio),
      and silently drops audio when segment params differ. Re-encoding through the
      concat filter rebuilds clean frame boundaries. Generate the inter-speaker
      silence inline at the SAME params as the TTS output (OpenAI TTS = 24 kHz mono)
      rather than from a static silence.mp3 that may mismatch.

      Build the whole scene in one pass. Example for 3 voice segments with 0.3s
      silence between speakers (interleave one `anullsrc` input between each segment):
      ```bash
      ffmpeg \
        -i scene-NN-seg-01.mp3 -f lavfi -t 0.3 -i anullsrc=r=24000:cl=mono \
        -i scene-NN-seg-02.mp3 -f lavfi -t 0.3 -i anullsrc=r=24000:cl=mono \
        -i scene-NN-seg-03.mp3 \
        -filter_complex "[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[out]" \
        -map "[out]" -c:a libmp3lame -ar 24000 -ac 1 -b:a 192k \
        story-output/audio/scene-NN.mp3
      ```
      Generalize: N voice segments → interleave (N-1) `anullsrc` silence inputs →
      `concat=n=(2N-1)`. Match `-ar`/`-ac`/`cl` to the actual TTS output params
      (confirm with `ffprobe` if unsure). A single voice segment needs no concat —
      just copy/encode it directly to scene-NN.mp3.
   d. Save final audio as story-output/audio/scene-NN.mp3
   e. Clean up temp segment files
   f. Log progress: "Generated audio for scene N of M"

11. Normalize audio levels across all scene files (optional, using FFmpeg loudnorm).

12. Verify all scene audio files exist.

13. Complete stage:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage narrate --output story-output/audio/
    ```

14. Check next and auto-continue:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" graph next
    ```
    If illustrate is still pending → invoke `/story:illustrate`
    If illustrate is complete → invoke `/story:build`
</process>
