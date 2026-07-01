#!/usr/bin/env bash
# nano-banana-image.sh — DEPRECATED shim.
#
# The CLI-based helper was replaced with a direct-REST implementation because
# the installed gemini nanobanana extension rejected --aspect and its /generate
# command was itself LLM-parsed (extra 429/503 surface).
# See docs/STORY-MAKER-ISSUES.md #1 for full context.
#
# This shim exists so any caller still referencing the .sh path still works.
# Callers SHOULD be updated to invoke nano-banana-image.py directly.
exec python3 "$(dirname "$0")/nano-banana-image.py" "$@"
