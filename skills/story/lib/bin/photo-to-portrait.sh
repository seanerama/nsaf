#!/usr/bin/env bash
# photo-to-portrait.sh — normalize a user-provided photo into a 1024×1024
# reference portrait for the illustrate stage to use as a Nano Banana ref.
#
# Usage:
#   photo-to-portrait.sh <source_image> <output_png>
#
#   <source_image>  Any FFmpeg-decodable image (.jpg, .jpeg, .png, .webp, .heic).
#   <output_png>    Destination path (parent dir must exist). Written as PNG
#                   regardless of source format.
#
# Behaviour:
#   Center-crops + scales the source to exactly 1024×1024 using lanczos, no
#   letterbox bars. That matches the aspect + dimensions that
#   nano-banana-image.sh writes when generating AI portraits, so downstream
#   `illustrate` treats the two sources interchangeably.
#
# Rationale:
#   The `illustrate` stage passes portrait PNGs to Nano Banana / Gemini Flash
#   as reference images conditioning scene renders. Whether the portrait was
#   AI-generated (nano-banana-image.sh) or is a user-supplied photo of a real
#   person/pet, the shape and quality contract is the same: 1024 square,
#   single subject, decent framing.
#
# Exit non-zero on any failure.

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <source_image> <output_png>" >&2
  exit 2
fi

SRC="$1"
OUT="$2"

if [ ! -f "$SRC" ]; then
  echo "source photo not found: $SRC" >&2
  exit 3
fi

command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not on PATH" >&2; exit 4; }

TARGET_W=1024
TARGET_H=1024

ffmpeg -y -loglevel error -i "$SRC" \
  -vf "scale=${TARGET_W}:${TARGET_H}:force_original_aspect_ratio=increase:flags=lanczos,crop=${TARGET_W}:${TARGET_H}" \
  -frames:v 1 "$OUT"

if [ ! -s "$OUT" ]; then
  echo "ffmpeg produced empty output at $OUT" >&2
  exit 5
fi

echo "wrote $OUT (from photo: $SRC)"
