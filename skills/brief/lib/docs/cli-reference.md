# CLI Reference

The `brief` command is the engine behind Daily-Brief. It does all the deterministic work —
managing profiles, history, deduplication, and rendering — and contains **no AI logic**. The
slash commands (`/brief:run`, `/brief:topic`, …) call these under the hood.

Most days you'll only touch `brief init`, `brief status`, and `brief profile`. The rest are the
building blocks the slash commands orchestrate; they're documented here for transparency,
scripting, and debugging.

> **Tip:** every command honors the `BRIEF_DATA_DIR` environment variable to point at a custom
> data folder (default: `./data`).

---

## Everyday commands

### `brief init [--force]`
Create the `data/` tree and the built-in **General** profile. `--force` overwrites an existing
General profile.

```bash
brief init
```

### `brief status [--json]`
Show every profile with its topic count, history size, and most recent run, plus overall
totals. `--json` emits a machine-readable report.

```bash
brief status
brief status --json
```

### `brief profile …`
Manage profiles.

| Command | Description |
|---------|-------------|
| `brief profile list [--json]` | List profile slugs and titles. |
| `brief profile show <slug> [--json]` | Show a parsed profile (topics + sources). |
| `brief profile create <slug> --title <t> --description <d> [--from-sample] [--force]` | Scaffold a new profile's `reference.md` plus empty history and knowledge-base files. `--from-sample` seeds example topics; `--force` overwrites. |

```bash
brief profile create realtor --title "Realtor" \
  --description "a realtor tracking local housing trends" --from-sample
brief profile show realtor
```

---

## Pipeline commands

These are the deterministic steps a brief run is built from. The `/brief:run` and
`/brief:topic` commands call them in order, feeding in the research that AI sub-agents produced.
`<timestamp>` is a run id in `YYYY-MM-DD-HHMM` form.

### `brief dedup <slug> --items-file <path> [--mode annotate|drop]`
Read a JSON list of items, assign each a stable id, and compare against the profile's history.
In `annotate` mode (default) previously-seen items are kept and tagged with prior coverage; in
`drop` mode they're removed. Prints the resulting items as JSON.

### `brief assemble <slug> <timestamp> --trigger <run|topic> --started-at <iso> --items-file <path> [--requested-topic <t>] [--failures-file <path>]`
Combine deduped+framed items (and any source failures) into a `BriefRun`, compute stats, write
`run.json` into the run directory, and print its path.

### `brief render <slug> <timestamp> [--run-file <path>]`
Render `brief.html` and `summary.md` into the run directory. Defaults to reading
`<run-dir>/run.json` if `--run-file` isn't given.

### `brief podcast-prompt <slug> <timestamp>`
Build the NotebookLM-style two-host podcast prompt from the run's `summary.md` (framed by the
profile) and print it to stdout. The script itself is written by an AI sub-agent from this prompt.

### `brief history-from-run <slug> <timestamp>`
Derive history entries from a run's `run.json` and append them to the profile's history. Prints
the number appended.

### `brief run-dir <slug> --timestamp <timestamp>`
Create and print a run directory path (`data/briefs/<slug>/<timestamp>/`).

---

## History & knowledge-base commands

### `brief history add <slug> --json-file <path>`
Append history entries from a JSON list of entry objects. Prints the count appended.

### `brief kb-append <slug> --json-file <path>`
Append dated learnings to the profile's knowledge base. The JSON file looks like:

```json
{ "date": "2026-06-29", "learnings": ["Opus 4.8 ships a 1M context window"] }
```

Prints the number of learnings written.

---

## Exit codes & errors

- Commands exit non-zero on hard errors (e.g. a missing profile, an unreadable file).
- **Per-source failures during a run are not errors** — they're recorded in `run.json` and shown
  in the brief under "Could not fetch", so one unreachable source never sinks a whole run.

---

## File formats this CLI reads/writes

- **`reference.md`** — see the [Profiles guide](profiles.md).
- **`history.md`** — a markdown table; append-only.
- **`run.json`** — the full record of a run (profile, trigger, items, failures, stats).
- **`brief.html` / `summary.md` / `podcast-script.md`** — the three outputs per run.

For the user-facing workflow, see the [User Guide](user-guide.md).
