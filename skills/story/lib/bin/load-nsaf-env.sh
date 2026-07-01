#!/usr/bin/env bash
# load-nsaf-env.sh — parse ~/nsaf/.env safely and export its variables.
#
# Design:
#   Do NOT `source` the file. `source` executes shell metacharacters, so any
#   unquoted `|`, `$`, backtick, space, `&`, etc. in a value (e.g.
#   COOLIFY_API_TOKEN=id|secret) aborts the caller under `set -e` with a
#   "command not found" error before the API key we actually need is loaded.
#
#   Instead: parse KEY=VALUE line by line, strip surrounding quotes if any,
#   and export via `printf -v` + `export -n` — no shell evaluation of the
#   value. Works for any value that fits the dotenv convention (arbitrary
#   bytes except newlines and NUL).
#
# Usage:
#   source .../load-nsaf-env.sh                # loads ~/nsaf/.env into env
#   source .../load-nsaf-env.sh /path/to/.env  # loads a specific file
#
# Comments (# ...) and blank lines are skipped. Lines that don't match
# KEY=VALUE are silently ignored (with a warn to stderr) — this preserves
# forward-compat if the file has unusual sections.

__load_nsaf_env() {
  local env_file="${1:-$HOME/nsaf/.env}"
  [ -f "$env_file" ] || return 0  # no file → no-op, don't error

  local line key value
  while IFS= read -r line || [ -n "$line" ]; do
    # Skip blanks and comments (leading # after optional whitespace)
    case "$line" in
      ''|[[:space:]]*'#'*|'#'*) continue ;;
    esac

    # Split on FIRST `=` only (values may contain `=`).
    key="${line%%=*}"
    value="${line#*=}"

    # Trim whitespace from key (keys shouldn't have any, but be safe).
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    # Skip lines that don't look like KEY=VALUE (no `=` sign or bad key name)
    if [ "$key" = "$line" ] || ! [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      # Not a valid assignment; skip silently (comments, section headers, etc.)
      continue
    fi

    # Strip surrounding quotes if the value is wrapped in matching '' or ""
    # (dotenv convention). Don't process escapes — treat value as opaque bytes.
    if [ "${value#\"}" != "$value" ] && [ "${value%\"}" != "$value" ]; then
      value="${value#\"}"
      value="${value%\"}"
    elif [ "${value#\'}" != "$value" ] && [ "${value%\'}" != "$value" ]; then
      value="${value#\'}"
      value="${value%\'}"
    fi

    # Export via printf -v to a namespaced local, then `export` — no eval.
    printf -v "$key" '%s' "$value"
    export "$key"
  done < "$env_file"
}

__load_nsaf_env "$@"
unset -f __load_nsaf_env
