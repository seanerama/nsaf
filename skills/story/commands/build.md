---
name: story:build
description: Assemble images and audio into final MP4 video
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---
<objective>
Combine scene illustrations and narration audio into a final MP4 video
with transitions, title card, and credits. YouTube-uploadable quality.

Produces: story-output/final.mp4
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage build`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage build
   ```
   Verify both illustrate and narrate are complete.

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage build
   ```

3. Read config for build settings:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" config get
   ```
   Get: resolution, scene_transition, transition_duration, title_card_duration, credits_duration

4. **Pre-flight check**:
   - List all story-output/images/scene-*.png files
   - List all story-output/audio/scene-*.mp3 files
   - Verify 1:1 matching by scene number
   - Verify FFmpeg is installed: `ffmpeg -version`
   - If any check fails, report the specific issue and stop

5. Read story-output/concept.md for the story title (for title card).

6. **Detect audio params** from the first scene audio (so title/credits match):
   ```bash
   SAMPLE_RATE=$(ffprobe -v quiet -show_entries stream=sample_rate -of csv=p=0 story-output/audio/scene-01.mp3)
   CHANNELS=$(ffprobe -v quiet -show_entries stream=channels -of csv=p=0 story-output/audio/scene-01.mp3)
   CH_LAYOUT=$([ "$CHANNELS" = "1" ] && echo "mono" || echo "stereo")
   ```
   IMPORTANT: Title and credits audio MUST match scene audio params exactly,
   otherwise `-c copy` concat will drop the audio stream silently.

7. **Generate title card**:
   ```bash
   ffmpeg -y -f lavfi -i color=c=0x1a1a2e:s=1920x1080:d=4 \
     -f lavfi -i anullsrc=r=${SAMPLE_RATE}:cl=${CH_LAYOUT} \
     -vf "drawtext=text='Story Title':fontsize=72:fontcolor=0xf0e6d3:x=(w-text_w)/2:y=(h-text_h)/2" \
     -c:v libx264 -c:a aac -b:a 192k -shortest -pix_fmt yuv420p \
     story-output/temp/title.mp4
   ```

7. **Assemble per-scene video clips**:
   For each scene (and title card):
   ```bash
   ffmpeg -loop 1 -i story-output/images/scene-NN.png \
     -i story-output/audio/scene-NN.mp3 \
     -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
     -shortest -pix_fmt yuv420p \
     story-output/temp/scene-NN.mp4
   ```

8. **Create concat list** (story-output/temp/concat.txt):
   ```
   file 'title.mp4'
   file 'scene-01.mp4'
   file 'scene-02.mp4'
   ...
   file 'credits.mp4'
   ```

9. **Generate credits clip** (must use same audio params as scenes):
   ```bash
   ffmpeg -y -f lavfi -i color=c=0x1a1a2e:s=1920x1080:d=3 \
     -f lavfi -i anullsrc=r=${SAMPLE_RATE}:cl=${CH_LAYOUT} \
     -vf "drawtext=text='Created with Story Maker':fontsize=48:fontcolor=0xf0e6d3:x=(w-text_w)/2:y=(h-text_h)/2" \
     -c:v libx264 -c:a aac -b:a 192k -shortest -pix_fmt yuv420p \
     story-output/temp/credits.mp4
   ```

10. **Concatenate with transitions**:
    For crossfade transitions, use xfade filter:
    ```bash
    ffmpeg -f concat -safe 0 -i concat.txt \
      -c:v libx264 -c:a aac -pix_fmt yuv420p \
      story-output/final.mp4
    ```
    Or for simple concat without transitions (simpler, more reliable):
    ```bash
    ffmpeg -f concat -safe 0 -i concat.txt -c copy story-output/final.mp4
    ```

11. **Clean up temp files**:
    ```bash
    rm -rf story-output/temp/
    ```

12. **Verify output**:
    ```bash
    ffprobe -v quiet -print_format json -show_format story-output/final.mp4
    ```
    Report: duration, file size, resolution.

13. Complete stage:
    ```bash
    node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage build --output story-output/final.mp4
    ```

14. Announce completion:
    - "Your story is ready! 🎬"
    - Report: story-output/final.mp4, duration, file size
    - Suggest: "Upload to YouTube or play locally"
</process>
