# Story Maker — Build Issues & Fixes (Freddie's Search for Bigfoot)

Hand-off notes for the agent that maintains the Story Maker pipeline. This story
completed end-to-end (MP4 + print PDF), but only after ~10 workarounds. Each item
below is written as **Symptom → Root cause → Workaround applied → Recommended fix**
so it can be triaged directly.

- **Date:** 2026-07-01
- **Project:** `~/nsaf/data/story/freddie-bigfoot/`
- **Pipeline stages run:** start → outline → write → portraits → narrate → illustrate → build → pdf
- **Providers:** images = Nano Banana (Gemini), TTS = ElevenLabs (switched from OpenAI mid-run)
- **Net result:** shipped, but the image path (`nano-banana-image.sh`) is effectively broken against the currently-installed extension and had to be bypassed entirely.

---

## Severity summary

| # | Issue | Impact | Where |
|---|-------|--------|-------|
| 1 | `nano-banana-image.sh` incompatible with installed nanobanana extension (`--aspect` rejected) | **Blocker** — no images at all via the supported path | `~/.claude/story/bin/nano-banana-image.sh` + extension |
| 2 | `NANOBANANA_MODEL` pinned to overloaded/limited `gemini-3-pro-image` | **Blocker** — ~1 hr of 503s, then quota | `~/nsaf/.env` |
| 3 | Gemini CLI reads `GEMINI_API_KEY`, but the working prepaid key was under `GOOGLE_API_KEY`/`NANOBANANA_API_KEY` | **Blocker** — used an exhausted free-tier key | `~/nsaf/.env` + helper |
| 4 | Helper `source`s `~/nsaf/.env`; unquoted value with `|` broke `set -e` sourcing | **Blocker** — aborted before key loaded | `nano-banana-image.sh` |
| 5 | `state complete-stage portraits` doesn't persist to `completed_stages` | **Blocker** — illustrate dep check failed after portraits done | `story-tools.cjs` / `templates/state.md` |
| 6 | Opaque/ truncated API errors; 429-quota looked like transient 503 | High — wasted ~1 hr retrying an unrecoverable state | `nano-banana-image.sh` |
| 7 | `pick-voice.cjs` ElevenLabs path returns unusable `SEARCH:` queries; `/v2/voices?search=` matches name only | Medium — manual voice casting required | `pick-voice.cjs` |
| 8 | OpenAI voice picker collision (two distinct chars → same voice) | Medium — brothers would sound identical | `pick-voice.cjs` |
| 9 | `make-print-pdf.cjs` renderer detection too narrow (misses Playwright chromium) | Medium — PDF stage can't find a browser | `make-print-pdf.cjs` |
| 10 | Stray `scene-01.mp3` at wrong sample rate survived provider switch | Low — resumability skip is provider-blind | narrate stage |
| 11 | STATE.md markdown checklist (6 items) disagrees with graph (8 stages) | Low — confusing state display | `templates/state.md` |

---

## 1. `nano-banana-image.sh` is version-incompatible with the installed extension  ⚠️ biggest issue

**Symptom.** Every image call via the helper failed. When it finally reached the
CLI cleanly, the error was:
```
Error: Invalid option(s) found: --aspect=1:1. Valid options are: --count (1-8),
--styles, --variations, --format (grid or separate), --seed, --preview
```

**Root cause.** `~/.claude/story/bin/nano-banana-image.sh` builds
`gemini --yolo "/generate '<prompt>' --aspect=$ASPECT"` (and `/edit ref... --aspect`).
The **currently installed** nanobanana extension
(`~/.gemini/extensions/nanobanana/commands/generate.toml`) is an **LLM-parsed
command** whose valid flags are `--count/--styles/--variations/--format/--seed/--preview`
— there is **no `--aspect`**. So the helper's invocation is rejected outright.
Worse, that `/generate` command is parsed by a **router LLM call** (uses
`gemini-2.5-flash-lite`) *before* the image tool runs — a second, independent
failure point that also hit quota/503 (see #2, #3, #6).

**Workaround applied.** Bypassed the gemini CLI + extension entirely and called the
Gemini REST API directly (`:generateContent`). This removed both the `--aspect`
incompatibility and the router-LLM pre-call. New helper written at
`story-output/gen_image.py`:
- `POST https://generativelanguage.googleapis.com/v1beta/models/<MODEL>:generateContent`
- Aspect ratio via `generationConfig.imageConfig.aspectRatio` (with graceful drop
  to ffmpeg center-crop if the field 400s on older API), then ffmpeg
  scale+crop to the exact contract size (1024² / 1920×1080).
- **Reference images (photo-anchoring) preserved**: refs are attached as
  `inlineData` image parts plus a "preserve each character's identity" compose
  prompt. This produced excellent likeness on the real-photo characters.
- First REST call succeeded instantly — **no 503, no quota error** — proving the
  problem was the CLI wrapper, not the key or Google capacity at that point.

**Recommended fix.** Replace the CLI-based `nano-banana-image.sh` with a direct
REST implementation (see `gen_image.py` in this project as a working reference).
Direct REST is the robust 2025 path: one HTTP call, explicit model, no router LLM,
no extension-version drift, supports multi-image reference conditioning. If the CLI
path is kept, it must (a) detect the installed extension's command schema and (b)
stop passing `--aspect`.

---

## 2. `NANOBANANA_MODEL` pinned to `gemini-3-pro-image` (overloaded + limited)

**Symptom.** ~1 hour of continuous `503 UNAVAILABLE "This model is currently
experiencing high demand"` on every image attempt (30+ retries). Earlier, on the
free-tier key, the same model reported `free_tier_requests, limit: 0`.

**Root cause.** `~/nsaf/.env` set `NANOBANANA_MODEL=gemini-3-pro-image`. The pro
image model is heavily rate-limited / capacity-constrained. The nanobanana
extension's **own default is `gemini-3.1-flash-image-preview`** (per its README),
which is lighter and had capacity. The env override forced the worst model.

**Workaround applied.** Switched to a flash image model. Final working model was
`gemini-2.5-flash-image` (via the REST helper), which returned images immediately.
`gemini-3.1-flash-image` is also available on the key and would work too.

**Recommended fix.** Default `NANOBANANA_MODEL` to a flash image model
(`gemini-2.5-flash-image` or `gemini-3.1-flash-image`). Add model-fallback: on
persistent 503, automatically retry against an alternate image model rather than
hammering one. Document that `gemini-3-pro-image` is high-quality but frequently
throttled.

---

## 3. Wrong env var held the working key (`GEMINI_API_KEY` vs `GOOGLE_API_KEY`)

**Symptom.** Persistent `429 … You have exhausted your daily quota on this model`
even after the user "added a paid key." The active key ended in `…aW8M`.

**Root cause.** The gemini CLI and `nano-banana-image.sh` read **`GEMINI_API_KEY`**.
In `~/nsaf/.env`, `GEMINI_API_KEY` held a **free-tier** key (`…aW8M`, exhausted),
while the user's **prepaid** key (`…qR8g`) was only under `GOOGLE_API_KEY` (line 8)
and `NANOBANANA_API_KEY` (line 64). So the pipeline never used the paid key.
Note: when both `GOOGLE_API_KEY` and `GEMINI_API_KEY` are set, the gemini CLI logs
"Using GOOGLE_API_KEY" — inconsistent precedence that compounds the confusion.

**Workaround applied.** Set `GEMINI_API_KEY` = the prepaid key's value (copied from
`GOOGLE_API_KEY`). Immediately cleared the 429s. Backup at
`~/nsaf/.env.bak-gemini-key-fix`.

**Recommended fix.** Document the exact env var the image path consumes. Consider
having the helper accept any of `GEMINI_API_KEY` / `GOOGLE_API_KEY` /
`NANOBANANA_API_KEY` (first non-empty) so a key in any of the conventional slots
works. On a 429, surface which key (masked tail) and which metric/limit tripped.

---

## 4. Helper `source`s `~/nsaf/.env`; a value with `|` broke sourcing under `set -e`

**Symptom.** First image attempt failed with:
```
/home/smahoney/nsaf/.env: line 51: AnDKIrBC…: command not found
```
and the script aborted before generating anything.

**Root cause.** The helper does `set -a; source ~/nsaf/.env`. Line 51 was
`COOLIFY_API_TOKEN=<id>|<secret>` — an **unquoted pipe**. `source` executes shell
metacharacters, so bash tried to run the text after `|` as a command; under
`set -euo pipefail` the non-zero exit aborted the whole script before the Gemini
key ever loaded.

**Workaround applied.** Quoted the value on line 51 (`COOLIFY_API_TOKEN="…"`).
Backup at `~/nsaf/.env.bak-portraits-fix`.

**Recommended fix.** Do **not** `source` the env file. Parse it safely
(line-by-line `KEY=VALUE`, no shell evaluation) — e.g. read into a map and export,
or `export $(grep -v '^#' file | xargs)` with proper quoting, or use a dotenv
parser. Any `.env` value containing `|`, `$`, backticks, spaces, `&`, etc. will
otherwise break `source`. This is a latent footgun for every pipeline that sources
this shared file.

---

## 5. `state complete-stage portraits` silently drops portraits from `completed_stages`  ⚠️ state bug

**Symptom.** After `complete-stage portraits` returned `{"completed": true}`, the
illustrate stage's dep check still reported `can_run: false, missing_deps:
["portraits"]`. `graph next` also kept re-listing `portraits` as available even
after "completing" it. `STATE.md` frontmatter `completed_stages` never contained
`"portraits"`.

**Root cause.** `story-output/STATE.md` is generated from
`~/.claude/story/templates/state.md`, whose markdown checklist lists only **6**
stages (Start, Outline, Write, Illustrate, Narrate, Build) — **no Portraits row**
— while the graph defines **8** stages (`total_stages: 8`, includes portraits and
pdf). `complete-stage portraits` appears to update the checklist (which has no
Portraits line) and its write of the frontmatter array doesn't retain portraits;
a subsequent `start-stage`/`complete-stage` then rewrites `completed_stages` from
a source that omits portraits, dropping it. Observed the array flip between
`[…,"narrate"]` and `[…,"illustrate","narrate"]` with portraits never present.

**Workaround applied.** Hand-edited `STATE.md` frontmatter to add `"portraits"` to
`completed_stages` so the illustrate dep check would pass.

**Recommended fix.** Make the state model track **all 8 graph stages** consistently:
add Portraits (and PDF) rows to `templates/state.md`, and ensure
`complete-stage`/`start-stage` read+write `completed_stages` from a single source
of truth (the graph), not the 6-item markdown checklist. Add a regression test:
complete portraits → assert it stays in `completed_stages` after a following
`start-stage illustrate`.

---

## 6. Opaque error surfacing — 429 (quota) masqueraded as 503 (transient)

**Symptom.** For ~1 hour the failures looked like transient overload (503), so
retrying seemed reasonable. The real state was partly an unrecoverable **429 daily
quota** on the wrong key. The helper truncated errors (`tail -2`), showing only a
trailing `}`.

**Root cause.** `nano-banana-image.sh` discards stderr detail and the CLI's error
JSON is deeply nested; the distinction between **429 (stop, fix billing/key)** and
**503 (retry)** was invisible without manually re-running the raw `gemini` command.

**Recommended fix.** Surface the classified error: on failure, print the HTTP
status and `error.status` (`RESOURCE_EXHAUSTED` vs `UNAVAILABLE`) and the offending
metric/model. Retry only on 500/503; on 429 stop immediately with a clear
"quota/billing" message naming the key tail and model. The REST helper
(`gen_image.py`) already distinguishes these.

---

## 7. `pick-voice.cjs` ElevenLabs path is not usable as-is

**Symptom.** `pick-voice.cjs elevenlabs <age> <gender> <accent> <desc>` returned
`SEARCH:<query>` for every character (no local voice map present). Following the
documented resolution — `GET /v2/voices?search=<query>&voice_type=premade` — with
those descriptive queries returned **zero results** for all of them
(`warm storybook narrator`, `young boy`, etc.).

**Root cause.** The ElevenLabs `/v2/voices?search=` param matches primarily the
voice **name**, not the label/description fields, so descriptive queries miss.
Also `voice_type=premade`/`default` returned nothing until the param was dropped.
The premade set (21 voices) also lacks any genuine child voices — needed for a
story whose leads are a 7-yo and a 3-yo.

**Workaround applied.** Ignored `SEARCH:` and cast manually:
- Pulled the full premade list (`/v2/voices?page_size=100`) and matched by
  `labels.gender/age/descriptive` for the adults + narrator.
- Used the **shared voice library** (`/v1/shared-voices?search=…&gender=&age=`) to
  find real child voices for Freddie/Alden and an "old female" grandmother the
  premade set lacked. Confirmed each `voice_id` renders with a tiny TTS test
  before committing.
- Wrote the resolved IDs into `story-output/voice-assignments.json` and the outline
  Voice ID column.

**Recommended fix.** For ElevenLabs, resolve `SEARCH:` by (a) fetching the full
voice list and ranking by **label attributes** (gender/age/accent/descriptive),
not the `search=` name filter, and (b) optionally querying `/v1/shared-voices` when
the premade set has no match (notably for child/elderly voices). Cache a
`elevenlabs-voices.json` to make picks deterministic across runs.

---

## 8. OpenAI voice picker collides distinct characters onto one voice

**Symptom.** On the OpenAI provider, `pick-voice.cjs` returned `echo` for **both**
Freddie (7) and Alden (3) — the two lead brothers who trade dialogue constantly.

**Root cause.** OpenAI has only 6 voices; the deterministic map keyed on
(age band, gender, accent) collapses two young males to the same voice. No
collision-avoidance across a cast.

**Workaround applied.** Overrode Alden to a different voice for contrast (before we
switched providers to ElevenLabs entirely).

**Recommended fix.** Add cast-level de-duplication: when two characters resolve to
the same voice, nudge one to the next-best distinct voice (by the same attribute
ranking). Especially important for the tiny OpenAI voice set.

---

## 9. `make-print-pdf.cjs` renderer detection misses Playwright/puppeteer Chromium

**Symptom.** PDF stage pre-flight found "no PDF renderer" though a headless
Chromium existed on the machine.

**Root cause.** `make-print-pdf.cjs` only probes `google-chrome`,
`google-chrome-stable`, `chromium`, `chromium-browser`, and `wkhtmltopdf` via
`which`. The available browser was Playwright's bundled build at
`~/.cache/ms-playwright/chromium-1194/chrome-linux/chrome`, not on PATH under any
of those names.

**Workaround applied.** Symlinked the Playwright chrome as `chromium` on a temp
PATH dir, then ran the helper. Rendered a correct 11-page, 8.5×8.5" PDF.

**Recommended fix.** Extend the candidate list to also glob common bundled-browser
caches: `~/.cache/ms-playwright/chromium*/chrome-linux/chrome`,
`~/.cache/puppeteer/chrome/*/chrome-linux*/chrome`, and honor
`PUPPETEER_EXECUTABLE_PATH` / `CHROME_PATH` env vars. Note: standalone
`--screenshot` runs of the Playwright chrome need `--no-sandbox
--disable-dev-shm-usage` (the helper's PDF print path already worked without extra
flags).

---

## 10. Resumability skip-logic is provider-blind (stale `scene-01.mp3`)

**Symptom.** After switching TTS from OpenAI to ElevenLabs, scene 1 was skipped as
"exists" but was still a **24 kHz** file (OpenAI rate) while all other scenes were
**22.05 kHz** (ElevenLabs) — a mismatch that would surface in the concat.

**Root cause.** The narrate skip check is "file exists and non-empty"; it doesn't
record which provider/voice/sample-rate produced the file. A stray earlier artifact
(origin unclear; the OpenAI run was rejected) slipped through.

**Workaround applied.** Detected the odd 24 kHz via ffprobe, deleted and
regenerated scene 1 with ElevenLabs; verified all scenes at 22.05 kHz before build.

**Recommended fix.** On provider/model/voice change, invalidate cached audio (e.g.
stamp a small sidecar or the `voice-assignments.json` hash and re-render on
mismatch). At minimum, verify sample-rate consistency across scene audio before the
build stage.

---

## 11. STATE.md checklist (6) disagrees with the graph (8 stages)

**Symptom.** The human-readable "Completed Stages" checklist in `STATE.md` shows 6
items and never renders Portraits or PDF, while `progress.total_stages: 8`.

**Root cause.** `templates/state.md` predates the portraits + pdf stages.

**Recommended fix.** Regenerate the template checklist from the graph so all 8
stages appear and check off correctly. (Ties into #5.)

---

## Artifacts created during this build (candidates to fold into the tool)

All in `story-output/`, all working references:

- **`gen_image.py`** — direct-REST Gemini image gen with reference-image
  conditioning + ffmpeg crop to the size contract. Drop-in replacement concept for
  `nano-banana-image.sh`. **Most important to review.**
- **`illustrate.py`** — per-scene orchestration: parses `### Illustration Prompt`
  from `script.md`, maps present characters → portrait PNGs (cap 5), calls the gen
  helper, resumable.
- **`narrate.py`** — parses `[VOICE:x]` segments, calls ElevenLabs TTS
  (`mp3_22050_32`, `eleven_multilingual_v2`), concats per scene via ffmpeg concat
  filter with 0.3 s inter-speaker silence at matched sample rate.
- **`build.sh`** — title/credits cards + per-scene clips standardized to
  1920×1080 / 30 fps / AAC 44.1 k stereo, concatenated to `final.mp4`.

## Env files touched (backups left in place)

- `~/nsaf/.env` — quoted `COOLIFY_API_TOKEN` (#4); pointed `GEMINI_API_KEY` at the
  prepaid key (#3); set `NANOBANANA_MODEL=gemini-3.1-flash-image` (#2).
- Backups: `~/nsaf/.env.bak-portraits-fix`, `~/nsaf/.env.bak-gemini-key-fix`,
  `~/nsaf/.env.bak-model-switch`.

## One-line takeaway for the maintainer

The single highest-value fix is **replacing the gemini-CLI image path with direct
REST `:generateContent`** (kills issues #1, #2 partial, #6) and **defaulting to a
flash image model**; second is the **portraits state-tracking bug (#5)** that
breaks the dependency graph even on a clean run.
