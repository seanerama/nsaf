#!/usr/bin/env bash
# nano-banana-image.sh — generate one image via Nano Banana (Gemini CLI extension).
#
# Usage:
#   nano-banana-image.sh <output_png> <aspect> <prompt> [ref_image ...]
#
#   <output_png>   Final path to write (e.g. story-output/images/scene-03.png).
#                  Parent dir must exist.
#   <aspect>       "1:1" (portraits) or "16:9" (scenes).
#   <prompt>       Quoted prompt string.
#   [ref_image]    Zero or more existing PNG paths used as character/style refs.
#                  When given, the script uses the multi-image edit/compose path
#                  (Gemini conditions generation on each reference).
#
# Behaviour:
#   - 0 refs → `gemini --yolo "/generate '...' --aspect=AR"`.
#   - 1+ refs → `gemini --yolo "/edit ref1 ref2 ... 'compose prompt'"` (the
#     nanobanana extension's edit command accepts multiple reference files;
#     the prompt instructs Gemini to preserve character identity).
#   - Finds the newest file in ./nanobanana-output/ produced this run.
#   - Crops/pads to the configured target (1024x1024 for 1:1, 1920x1080 for
#     16:9) via FFmpeg lanczos so the pipeline output contract stays exact.
#
# Env:
#   GEMINI_API_KEY or NANOBANANA_GEMINI_API_KEY must be set (the gemini CLI
#   reads them itself; the script just verifies one is present).
#
# Exit non-zero on any failure (no images generated, gemini missing, etc.).

set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <output_png> <aspect 1:1|16:9> <prompt> [ref ...]" >&2
  exit 2
fi

OUT="$1"; shift
ASPECT="$1"; shift
PROMPT="$1"; shift
REFS=("$@")

case "$ASPECT" in
  1:1)  TARGET_W=1024; TARGET_H=1024 ;;
  16:9) TARGET_W=1920; TARGET_H=1080 ;;
  *) echo "aspect must be 1:1 or 16:9, got $ASPECT" >&2; exit 2 ;;
esac

if [ -z "${GEMINI_API_KEY:-${NANOBANANA_GEMINI_API_KEY:-}}" ]; then
  echo "GEMINI_API_KEY (or NANOBANANA_GEMINI_API_KEY) not set" >&2
  exit 3
fi

command -v gemini >/dev/null 2>&1 || { echo "gemini CLI not on PATH" >&2; exit 4; }
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not on PATH" >&2; exit 4; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Gemini CLI saves outputs to ./nanobanana-output/ in the current working dir,
# so run it from a clean per-call subdir to make "find newest" unambiguous.
cd "$WORK"
mkdir -p nanobanana-output

# Resolve each ref to an absolute path before we cd (callers pass relative paths).
ABS_REFS=()
for r in "${REFS[@]:-}"; do
  if [ -z "$r" ]; then continue; fi
  if [ ! -f "$r" ]; then
    echo "reference image not found: $r" >&2
    exit 5
  fi
  ABS_REFS+=("$(readlink -f "$r")")
done

if [ "${#ABS_REFS[@]}" -eq 0 ]; then
  # No refs → plain text-to-image.
  gemini --yolo "/generate '$PROMPT' --aspect=$ASPECT" >/dev/null
else
  # Refs present → ask Gemini to compose the scene while preserving every ref
  # subject's identity. Pass refs as positional file args to /edit.
  REF_ARG=""
  for r in "${ABS_REFS[@]}"; do
    REF_ARG+=" $(printf '%q' "$r")"
  done
  COMPOSE_PROMPT="Use each reference image as the canonical appearance of its character. Preserve face structure, hair, skin tone, clothing, and proportions exactly. Place these characters into the following scene: ${PROMPT}. Maintain the source art style. Aspect ratio ${ASPECT}."
  # shellcheck disable=SC2086
  gemini --yolo "/edit${REF_ARG} '$COMPOSE_PROMPT' --aspect=$ASPECT" >/dev/null
fi

# Newest file produced by this gemini run.
GEN="$(find nanobanana-output -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) -print0 \
       | xargs -0 ls -t 2>/dev/null | head -n1 || true)"

if [ -z "$GEN" ] || [ ! -f "$GEN" ]; then
  echo "no image produced in $WORK/nanobanana-output" >&2
  exit 6
fi

# Crop/pad to exact target resolution. `force_original_aspect_ratio=increase`
# scales the short side to cover, then crop centers it — no letterbox bars.
ffmpeg -y -loglevel error -i "$GEN" \
  -vf "scale=${TARGET_W}:${TARGET_H}:force_original_aspect_ratio=increase:flags=lanczos,crop=${TARGET_W}:${TARGET_H}" \
  -frames:v 1 "$OUT"

if [ ! -s "$OUT" ]; then
  echo "ffmpeg produced empty output at $OUT" >&2
  exit 7
fi

echo "wrote $OUT"
