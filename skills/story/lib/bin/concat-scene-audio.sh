#!/usr/bin/env bash
# concat-scene-audio.sh — polish + concatenate TTS segments into one scene mp3.
#
# The previous inline-ffmpeg approach concatenated raw TTS segments with 0.3 s
# of dead silence between them — no loudness match, no fade at boundaries.
# Result: perceived level jumps between voices ("clunky transitions") plus a
# hard-cut click at every start/end. This helper fixes both:
#
#   1. Per-segment loudness normalization to -16 LUFS via `loudnorm` (matches
#      each voice's perceived level across the scene — the biggest single
#      contributor to smoothness).
#   2. 25 ms fade-in at the start of every speech segment, 50 ms fade-out at
#      the end — softens the boundary between "voice audible" and "silence".
#   3. Silence between speakers is generated inline at the target sample rate
#      and channel layout, matching every polished segment exactly. The concat
#      filter (NOT `-c copy`) rebuilds clean frame boundaries.
#
# Usage:
#   concat-scene-audio.sh <output.mp3> <sample_rate> <pause_seconds> <seg1> <seg2> ...
#
#   <sample_rate>     22050 for ElevenLabs (mp3_22050_32) or 24000 for OpenAI
#                     tts-1-hd. All silence + concat happen at this rate.
#   <pause_seconds>   Inter-speaker silence duration. Typical: 0.3.
#   <seg*>            Ordered TTS segment mp3s.
#
# Behaviour:
#   - Single-segment scenes are still polished (loudnorm + fades) but skip the
#     concat step and copy directly to the output.
#   - Temp files are cleaned up on exit.
#   - Existing output is overwritten.
#
# Exit non-zero on any failure.

set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "usage: $0 <output.mp3> <sample_rate> <pause_seconds> <seg1> [seg2 ...]" >&2
  exit 2
fi

OUT="$1"; shift
SR="$1"; shift
PAUSE="$1"; shift
SEGS=("$@")

command -v ffmpeg >/dev/null 2>&1  || { echo "ffmpeg not on PATH"  >&2; exit 3; }
command -v ffprobe >/dev/null 2>&1 || { echo "ffprobe not on PATH" >&2; exit 3; }

# Sanity check every segment exists and is non-empty.
for s in "${SEGS[@]}"; do
  if [ ! -s "$s" ]; then
    echo "segment missing or empty: $s" >&2
    exit 4
  fi
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ── Polish each segment: loudnorm + fade-in + fade-out ─────────────────────
# We do a single-pass loudnorm (I=-16 LUFS, TP=-2 dB true peak, LRA=11 loudness
# range) — cheap and consistent enough for TTS speech. If you want the
# reference-quality two-pass loudnorm, replace the filter with a measured pass
# + apply pass; for storybook narration the single pass is inaudibly close.
FADE_IN_S=0.025
FADE_OUT_S=0.050

POLISHED=()
for i in "${!SEGS[@]}"; do
  src="${SEGS[$i]}"
  dst="$WORK/polished-$(printf '%02d' "$i").mp3"

  # Duration of source, to place the fade-out relative to the end.
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$src")
  # Guard against very short segments (<= fade_out) — skip the fade-out.
  awk_check=$(awk -v d="$dur" -v fo="$FADE_OUT_S" 'BEGIN { print (d > fo * 2) ? 1 : 0 }')

  if [ "$awk_check" = "1" ]; then
    fade_out_start=$(awk -v d="$dur" -v fo="$FADE_OUT_S" 'BEGIN { printf "%.3f", d - fo }')
    af="loudnorm=I=-16:TP=-2:LRA=11,afade=t=in:d=${FADE_IN_S},afade=t=out:st=${fade_out_start}:d=${FADE_OUT_S}"
  else
    # Segment is too short to fade both ends cleanly — just normalize + fade-in.
    af="loudnorm=I=-16:TP=-2:LRA=11,afade=t=in:d=${FADE_IN_S}"
  fi

  ffmpeg -y -loglevel error \
    -i "$src" \
    -af "$af" \
    -c:a libmp3lame -ar "$SR" -ac 1 -b:a 192k \
    "$dst"

  POLISHED+=("$dst")
done

# ── Concatenate ────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$OUT")"

if [ "${#POLISHED[@]}" -eq 1 ]; then
  # Single segment: just move the polished file into place.
  cp "${POLISHED[0]}" "$OUT"
  echo "wrote $OUT (1 segment, polished)"
  exit 0
fi

# Multi-segment: build the concat filter with interleaved silence.
INPUTS=()
LABELS=()
idx=0
for i in "${!POLISHED[@]}"; do
  INPUTS+=(-i "${POLISHED[$i]}")
  LABELS+=("[$idx:a]")
  idx=$((idx + 1))
  if [ "$i" -lt "$((${#POLISHED[@]} - 1))" ]; then
    INPUTS+=(-f lavfi -t "$PAUSE" -i "anullsrc=r=$SR:cl=mono")
    LABELS+=("[$idx:a]")
    idx=$((idx + 1))
  fi
done

FC="$(IFS=; echo "${LABELS[*]}")concat=n=${#LABELS[@]}:v=0:a=1[out]"

ffmpeg -y -loglevel error \
  "${INPUTS[@]}" \
  -filter_complex "$FC" \
  -map "[out]" \
  -c:a libmp3lame -ar "$SR" -ac 1 -b:a 192k \
  "$OUT"

echo "wrote $OUT (${#POLISHED[@]} segments polished + concatenated at ${SR} Hz, ${PAUSE}s pause)"
