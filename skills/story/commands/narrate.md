---
name: story:narrate
description: Generate multi-voice audio narration via TTS with cast-level dedup + loudness-matched transitions
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
and assemble per-scene audio files with multi-voice narration. Every scene
is polished via a per-segment loudnorm + fade-in/fade-out pass so voices
match perceived loudness and boundaries feel smooth — no more clunky level
jumps between speakers.

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

3. Read inputs:
   - `story-output/script.md` — narration sections with `[VOICE:name]` tags.
   - `story-output/outline.md` — Character Reference Sheet
     (columns: Name, Age, Gender, Accent, Visual Description, Portrait Prompt,
     Photo Path, Voice ID, Voice Description).

4. Load ~/nsaf/.env safely (no shell eval — protects against unquoted `|`
   values that used to abort the pipeline; see STORY-MAKER-ISSUES.md #4):
   ```bash
   source "$HOME/.claude/story/bin/load-nsaf-env.sh"
   ```
   Verify keys:
   - `OPENAI_API_KEY` (openai TTS) or `ELEVENLABS_API_KEY` (elevenlabs). If
     missing, pause and tell the user to add it to `~/nsaf/.env` — NOT to
     the project.

5. Read config:
   ```bash
   TTS_PROVIDER=$(node "$HOME/.claude/story/bin/story-tools.cjs" config get tts_provider --raw)
   TTS_MODEL=$(node "$HOME/.claude/story/bin/story-tools.cjs" config get tts_model --raw)
   ```

6. **Cast-level voice assignment (dedup'd, one call for the whole cast).**

   a. Build `story-output/cast.json` from the character reference sheet — one
      object per non-Narrator character plus one for the narrator:
      ```json
      [
        {"name": "narrator", "age": "-",  "gender": "-",      "accent": "neutral-us", "hint": "<Voice Description>"},
        {"name": "Freddie",  "age": "7",  "gender": "male",   "accent": "neutral-us", "hint": "curious brave boy"},
        {"name": "Alden",    "age": "3",  "gender": "male",   "accent": "neutral-us", "hint": "tiny toddler"}
      ]
      ```
      Character names MUST match the `[VOICE:name]` tags exactly (case-sensitive).

   b. Call the cast-level picker:
      ```bash
      node "$HOME/.claude/story/bin/pick-voice.cjs" cast "$TTS_PROVIDER" \
        story-output/cast.json --out story-output/voice-assignments.json
      ```
      The picker:
      - For openai: dedups across the cast (no more Freddie + Alden both
        getting `echo` — fixes #8).
      - For elevenlabs: fetches the full /v2/voices list, scores each by
        gender/age/accent/description labels (NOT the buggy name-only
        `search=` param), falls back to /v1/shared-voices when the premade
        set has no plausible match for child/elderly characters
        (fixes #7). Caches the voice list at
        `~/.claude/story/elevenlabs-voices-cache.json` for 24h.

   c. Write the resolved Voice ID back into `outline.md`'s reference sheet
      (Voice ID column) so re-runs are stable.

7. Ensure `story-output/audio/` and `story-output/audio/segments/` exist.

8. **Provider-aware resumability check** (fixes #10). For each scene:
   - If `scene-NN.mp3` exists AND
     `scene-NN.mp3.sidecar.json` exists AND
     the sidecar's `provider` + `voice_assignments_hash` match the CURRENT
     provider + current voice-assignments.json → **skip**.
   - Otherwise (missing sidecar, mismatched provider, or changed voice
     casting) → **delete stale artifacts and regenerate**. This prevents
     the "stale 24 kHz OpenAI file survives ElevenLabs re-render" failure.

9. For each scene that needs audio:

   a. Parse the scene's `### Narration` block into ordered
      `(voice_name, text)` segments by splitting on `[VOICE:name]` tags.
      Collapse internal whitespace/newlines within each segment to single
      spaces.

   b. Determine the TTS sample rate:
      - openai/tts-1-hd → 24000
      - elevenlabs (mp3_22050_32) → 22050

   c. For each segment `MM`, generate the raw TTS mp3 at
      `story-output/audio/segments/scene-NN-seg-MM.mp3`:

      **openai:**
      ```bash
      curl -s https://api.openai.com/v1/audio/speech \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$(jq -nc --arg v "<voice_id>" --arg t "<text>" \
              '{model:"tts-1-hd",voice:$v,input:$t}')" \
        --output "story-output/audio/segments/scene-NN-seg-MM.mp3"
      ```

      **elevenlabs:**
      ```bash
      curl -s "https://api.elevenlabs.io/v1/text-to-speech/<voice_id>?output_format=mp3_22050_32" \
        -H "xi-api-key: $ELEVENLABS_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$(jq -nc --arg t "<text>" '{text:$t,model_id:"eleven_multilingual_v2"}')" \
        --output "story-output/audio/segments/scene-NN-seg-MM.mp3"
      ```

   d. **Concatenate with the audio polish helper** (per-segment loudnorm at
      -16 LUFS + 25 ms fade-in + 50 ms fade-out + matched-rate silence
      between speakers — this fixes the "clunky transitions" complaint):
      ```bash
      bash "$HOME/.claude/story/bin/concat-scene-audio.sh" \
        "story-output/audio/scene-NN.mp3" \
        "$SR" 0.3 \
        story-output/audio/segments/scene-NN-seg-01.mp3 \
        story-output/audio/segments/scene-NN-seg-02.mp3 \
        ...
      ```
      Do NOT build the ffmpeg concat command inline — the helper handles
      loudnorm + fades + concat + single-segment case in one place.

   e. **Write the provider sidecar** so future re-runs can invalidate
      correctly on provider/cast changes:
      ```bash
      HASH=$(sha256sum story-output/voice-assignments.json | cut -c1-16)
      cat > "story-output/audio/scene-NN.mp3.sidecar.json" <<EOF
      {
        "provider": "$TTS_PROVIDER",
        "sample_rate": $SR,
        "voice_assignments_hash": "$HASH",
        "generated_at": "$(date -Iseconds)"
      }
      EOF
      ```

   f. Log: `"Generated audio for scene N of M (<segments> segments, provider=<TTS_PROVIDER>, sr=<SR>)"`.

10. Optional: cross-scene loudness normalization pass (all scenes to a
    common -16 LUFS integrated). The per-segment loudnorm inside each scene
    already handles per-voice level; this extra pass just aligns scene-to-
    scene averages if some scenes have more silence than others.

11. Verify all scene audio files exist AND all sidecars match the current
    provider hash.

12. Complete stage:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage narrate --output story-output/audio/
    ```

13. Check next and auto-continue:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" graph next
    ```
    If illustrate is still pending → invoke `/story:illustrate`
    If illustrate is complete → invoke `/story:build` (and optionally `/story:pdf`)
</process>

<notes>
- **Why the concat helper matters:** the old inline ffmpeg approach concatenated
  raw TTS segments with no loudness match and hard cuts at segment boundaries.
  Different voices at different perceived loudness produced the "clunky
  transitions" complaint. `concat-scene-audio.sh` applies loudnorm-16 LUFS per
  segment + 25 ms fade-in + 50 ms fade-out before concat, closing that gap.

- **Why cast-level dedup matters:** the old picker resolved each character
  independently. In a small cast with two young boys, both got `echo`
  (OpenAI's boy-adjacent voice) and sounded identical. Cast mode assigns
  Freddie → echo, Alden → nova. Same principle applies to ElevenLabs when
  two adults score similarly on the same premade voice.

- **Why the sidecar matters:** switching TTS providers mid-run used to leave
  a stale first scene at the old sample rate, silently corrupting the concat.
  The sidecar makes the resumability check provider-aware.

- **ELEVENLABS voice discovery:** `/v2/voices?search=<query>` matches VOICE
  NAMES, not label/description fields. Descriptive queries returned zero
  results. The picker instead fetches the full premade list and scores each
  voice against character labels — MUCH higher hit rate.

- **Child voice caveat:** ElevenLabs prohibits child-like voices in its public
  Voice Library. For child characters the picker falls back to
  `/v1/shared-voices` (community library, which has genuine child voices
  under different content-policy rules). If that also finds nothing, the
  closest "young" premade voice is used and a warning is logged.
</notes>
