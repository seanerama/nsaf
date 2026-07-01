#!/usr/bin/env python3
"""Direct-REST Gemini image generation for the story pipeline.

Replaces the flaky gemini-CLI + nanobanana-extension chain with a single
HTTPS call to `:generateContent`. Rationale (see docs/STORY-MAKER-ISSUES.md):

- The installed nanobanana extension rejected `--aspect`, and its `/generate`
  command was itself LLM-parsed (extra 429/503 surface).
- The pro image model was rate-limited into oblivion.
- Errors from the CLI came out truncated, so 429 (unrecoverable quota) looked
  like 503 (transient) and hammered the API for an hour.

This script fixes all three: one HTTP call, explicit model, explicit aspect,
classified errors (429 stops immediately, 500/503 retries with backoff).

Usage:
  nano-banana-image.py <output_png> <aspect> <prompt> [ref_image ...]

  <aspect>  "1:1" (portraits, 1024×1024) or "16:9" (scenes, 1920×1080)
  refs      0+ PNG paths passed as inlineData reference images. When present,
            the prompt is wrapped to instruct Gemini to preserve each
            reference character's identity — this is the photo-anchoring path.

Env vars consulted (first non-empty wins):
  API key:  GEMINI_API_KEY, GOOGLE_API_KEY, NANOBANANA_API_KEY
  Model:    NANOBANANA_MODEL (default: gemini-2.5-flash-image)
            Set to a flash image model. Do NOT pin to gemini-3-pro-image —
            it's rate-limited and will 503 for hours. If NANOBANANA_MODEL is
            set to a pro model AND we get 503s, the script falls back to
            gemini-2.5-flash-image automatically.

If ~/nsaf/.env exists, it is loaded (safely, no shell eval) before consulting
env vars — so callers don't need to pre-source anything.

Output is cropped/padded to exactly the target resolution via ffmpeg lanczos.

Exit codes: 0=ok, 2=usage, 3=missing key, 4=missing tool, 5=fatal API error,
6=no image produced, 7=ffmpeg failure.
"""
from __future__ import annotations
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# ─── Load ~/nsaf/.env safely ────────────────────────────────────────────────

def load_nsaf_env(path: str) -> None:
    """Line-by-line parser — no shell eval. Matches load-nsaf-env.sh."""
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                continue
            # Strip surrounding matched quotes.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # Don't overwrite already-set env (respect caller intent).
            os.environ.setdefault(key, value)


load_nsaf_env(os.path.expanduser("~/nsaf/.env"))

# ─── Args + config ──────────────────────────────────────────────────────────

if len(sys.argv) < 4:
    print("usage: nano-banana-image.py <out.png> <1:1|16:9> <prompt> [ref ...]", file=sys.stderr)
    sys.exit(2)

out_path = sys.argv[1]
aspect   = sys.argv[2]
prompt   = sys.argv[3]
refs     = sys.argv[4:]

TARGETS = {"1:1": (1024, 1024), "16:9": (1920, 1080)}
if aspect not in TARGETS:
    print(f"aspect must be 1:1 or 16:9, got {aspect}", file=sys.stderr)
    sys.exit(2)
TARGET_W, TARGET_H = TARGETS[aspect]

# Key precedence: GEMINI_API_KEY, GOOGLE_API_KEY, NANOBANANA_API_KEY.
# First non-empty wins. This lets a user keep any of the three names and
# have the pipeline just work — no more silent free-tier-key-in-wrong-var.
KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or os.environ.get("NANOBANANA_API_KEY")
)
if not KEY:
    print(
        "no GEMINI_API_KEY / GOOGLE_API_KEY / NANOBANANA_API_KEY set. "
        "Add one to ~/nsaf/.env.",
        file=sys.stderr,
    )
    sys.exit(3)

# Sanity: 39-char Google-style key starting with AIza.
def mask(k: str) -> str:
    return f"...{k[-4:]}" if k and len(k) >= 4 else "…"

PRIMARY_MODEL = os.environ.get("NANOBANANA_MODEL", "gemini-2.5-flash-image").strip()
FLASH_FALLBACK = "gemini-2.5-flash-image"

# Which models we consider "pro" (rate-limited, worth auto-falling-back away from)
PRO_MARKERS = ("gemini-3-pro-image", "gemini-3.5-pro-image")

for tool in ("ffmpeg",):
    r = subprocess.run(["which", tool], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"{tool} not on PATH", file=sys.stderr)
        sys.exit(4)

# ─── Build request body ─────────────────────────────────────────────────────

def build_body(with_aspect: bool) -> dict:
    parts: list[dict] = []
    for r in refs:
        if not os.path.isfile(r):
            print(f"reference image not found: {r}", file=sys.stderr)
            sys.exit(5)
        with open(r, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        ext = os.path.splitext(r)[1].lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext or 'png'}"
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})

    if refs:
        text = (
            "Use each provided reference image as the canonical appearance of its "
            "character. Preserve face structure, hair, skin tone, clothing, and "
            "proportions exactly. Compose them into this scene: "
            + prompt
            + f" Rendered in a {aspect} aspect ratio."
        )
    else:
        text = prompt + f" Rendered in a {aspect} aspect ratio."
    parts.append({"text": text})

    body: dict = {"contents": [{"parts": parts}]}
    if with_aspect:
        body["generationConfig"] = {"imageConfig": {"aspectRatio": aspect}}
    return body

# ─── Call ──────────────────────────────────────────────────────────────────

def call(model: str, body: dict) -> tuple[int, dict | bytes, str | None]:
    """Return (http_status, parsed_or_raw_body, error_message)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={KEY}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.load(r), None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            parsed = raw
        return e.code, parsed, str(e)
    except urllib.error.URLError as e:
        return 0, b"", f"URLError: {e}"

def extract_error_status(payload) -> tuple[str | None, str | None]:
    """Pull error.status and error.message out of a Google API error body."""
    if not isinstance(payload, dict):
        return None, None
    err = payload.get("error") or {}
    return err.get("status"), err.get("message")

def extract_image_bytes(payload) -> bytes | None:
    if not isinstance(payload, dict):
        return None
    try:
        for p in payload["candidates"][0]["content"]["parts"]:
            if "inlineData" in p:
                return base64.b64decode(p["inlineData"]["data"])
    except (KeyError, IndexError, TypeError):
        return None
    return None

def try_model(model: str, with_aspect: bool) -> tuple[bool, bytes | None, str]:
    """Return (ok, image_bytes, message)."""
    body = build_body(with_aspect)
    last_msg = ""
    for attempt in range(1, 5):
        code, payload, err = call(model, body)
        if code == 200 and isinstance(payload, dict):
            img = extract_image_bytes(payload)
            if img:
                return True, img, f"ok via {model}"
            last_msg = f"200 but no image parts: {json.dumps(payload)[:200]}"
            time.sleep(5)
            continue

        status, message = extract_error_status(payload)
        header = f"{model} attempt {attempt}: HTTP {code}"
        if status:
            header += f" ({status})"
        if message:
            header += f": {message[:200]}"
        print(header, file=sys.stderr)
        last_msg = header

        # 400 sometimes means the imageConfig field isn't supported → retry once without it.
        if code == 400 and with_aspect:
            print(
                f"  → 400 with imageConfig; retrying without generationConfig",
                file=sys.stderr,
            )
            body = build_body(with_aspect=False)
            with_aspect = False
            continue

        # 429 → quota. Do NOT retry. Surface which key + model.
        if code == 429 or status == "RESOURCE_EXHAUSTED":
            return False, None, (
                f"quota exhausted (429/RESOURCE_EXHAUSTED) for key {mask(KEY)} "
                f"on model {model}. {message or ''}"
            ).strip()

        # 503 / 500 / 504 / network → backoff + retry.
        if code in (500, 502, 503, 504) or code == 0:
            wait = 15 * attempt
            print(f"  → transient, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue

        # 401 / 403 → key problem, don't retry.
        if code in (401, 403):
            return False, None, f"auth error {code}: {message or ''} (key {mask(KEY)})"

        # Unknown → one small backoff then try again.
        time.sleep(5)

    return False, None, last_msg or f"{model}: exhausted retries"

# ─── Main flow: try primary, then flash fallback if primary is pro ─────────

print(f"gen: model={PRIMARY_MODEL} key={mask(KEY)} aspect={aspect} refs={len(refs)}", file=sys.stderr)
ok, img, msg = try_model(PRIMARY_MODEL, with_aspect=True)

if not ok and any(m in PRIMARY_MODEL for m in PRO_MARKERS) and PRIMARY_MODEL != FLASH_FALLBACK:
    print(f"primary model failed ({msg}); falling back to {FLASH_FALLBACK}", file=sys.stderr)
    ok, img, msg = try_model(FLASH_FALLBACK, with_aspect=True)

if not ok or img is None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(5)

# ─── Crop/pad to exact target resolution ────────────────────────────────────

os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
    tf.write(img)
    raw_path = tf.name

try:
    r = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", raw_path,
            "-vf",
            (
                f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase:"
                f"flags=lanczos,crop={TARGET_W}:{TARGET_H}"
            ),
            "-frames:v", "1", out_path,
        ],
        check=False,
    )
finally:
    os.unlink(raw_path)

if r.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
    print(f"ffmpeg failed to produce {out_path}", file=sys.stderr)
    sys.exit(7)

print(f"wrote {out_path} ({os.path.getsize(out_path)} bytes) via {msg}")
