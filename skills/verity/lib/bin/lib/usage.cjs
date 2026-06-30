// Usage ledger — `.verity/usage.csv` + `verity usage` CLI (T11, SKETCH §3.4)
// and the daily-limit rollup the worker's §4.1 startup check consumes.
//
// CSV contract (§3.4): header row REQUIRED, append-only, one row per worker run:
//
//   timestamp,run_id,repo,roles,tokens_in,tokens_out,est_usd,wall_secs,outcome
//
// Field encodings:
//   - timestamp  ISO-8601 UTC (new Date().toISOString())
//   - roles      role names joined with '+' (e.g. plan+build+review) so the
//                cell never needs CSV quoting; '' when no roles ran
//   - est_usd    decimal (≤4 places); '' when the run had no cost estimate
//   - all cells  RFC-4180 escaped anyway (quoted iff containing , " or newline)
//
// TIMEZONE: all day-windowing ("today", `--days N`) is UTC calendar days —
// the ledger stores UTC timestamps and the worker may run from any machine or
// CI runner, so local time would make the daily budget depend on where the
// worker happens to wake up. `--days N` = the last N UTC calendar days
// INCLUDING today (so `--days 1` = today UTC).
//
// MALFORMED INPUT: a missing usage.csv is an empty ledger; malformed rows
// (wrong column count, unparsable numbers/timestamp) are SKIPPED with a
// warning rather than failing the command — the ledger is append-only
// bookkeeping and one corrupt line must not brick `verity usage` or the
// worker's startup check (which would otherwise fail CLOSED and halt
// autonomy over a typo).
//
// The optional git commit (`chore(verity): usage <run-id>`, policy
// `commit_usage: true`, default true) commits ONLY the csv path and NEVER
// throws — a failed commit (not a repo, no git identity, etc.) is reported in
// the return value for the caller to log; the run's outcome must not change.
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const COLUMNS = [
  'timestamp',
  'run_id',
  'repo',
  'roles',
  'tokens_in',
  'tokens_out',
  'est_usd',
  'wall_secs',
  'outcome',
];
const HEADER = COLUMNS.join(',');
const CSV_REL_PATH = path.join('.verity', 'usage.csv');

function usagePath(cwd) {
  return path.join(cwd, CSV_REL_PATH);
}

// --- CSV encode/decode (RFC 4180 subset; zero-dep) ---------------------------

function escapeCell(value) {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Split one CSV line into cells, honoring double-quoted cells with "" escapes.
// Returns null when the line is structurally broken (unterminated quote).
function splitCsvLine(line) {
  const cells = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const c = line[i];
    if (quoted) {
      if (c === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        cur += c;
      }
    } else if (c === '"' && cur === '') {
      quoted = true;
    } else if (c === ',') {
      cells.push(cur);
      cur = '';
    } else {
      cur += c;
    }
  }
  if (quoted) {
    return null;
  }
  cells.push(cur);
  return cells;
}

// --- append (write side) ------------------------------------------------------

// Worker summary ({ runId, repo, outcome, roles, tokens:{in,out}, est_usd,
// wall_secs }) → ordered row object matching COLUMNS.
function entryFromSummary(summary, now = new Date()) {
  return {
    timestamp: now.toISOString(),
    run_id: summary.runId,
    repo: summary.repo,
    roles: (summary.roles || []).join('+'),
    tokens_in: summary.tokens?.in || 0,
    tokens_out: summary.tokens?.out || 0,
    est_usd: typeof summary.est_usd === 'number' ? Number(summary.est_usd.toFixed(4)) : '',
    wall_secs: summary.wall_secs || 0,
    outcome: summary.outcome,
  };
}

function formatRow(entry) {
  return COLUMNS.map((c) => escapeCell(entry[c])).join(',');
}

// Append one §3.4 row; create the file (with the required header) and the
// .verity dir if missing. Append-only: never rewrites existing content.
function appendUsage(cwd, entry) {
  const file = usagePath(cwd);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (!fs.existsSync(file)) {
    fs.writeFileSync(file, `${HEADER}\n`);
  }
  const row = formatRow(entry);
  fs.appendFileSync(file, `${row}\n`);
  return { path: file, row };
}

// `git add` + `git commit` of ONLY the csv path, message
// `chore(verity): usage <run-id>`. Never throws: returns
// { committed: true } or { committed: false, error } — callers log and continue
// (a broken git setup must never fail the run).
function commitUsage(cwd, runId) {
  const message = `chore(verity): usage ${runId}`;
  try {
    execFileSync('git', ['-C', cwd, 'add', '--', CSV_REL_PATH], { stdio: 'pipe' });
    execFileSync('git', ['-C', cwd, 'commit', '-m', message, '--', CSV_REL_PATH], {
      stdio: 'pipe',
    });
    return { committed: true, message };
  } catch (err) {
    const stderr = err.stderr ? String(err.stderr).trim() : '';
    return { committed: false, message, error: stderr.split('\n')[0] || err.message };
  }
}

// One-call write side for the worker: append the row, then commit when the
// policy says so. The append can throw (disk full etc. — caller's choice);
// the commit never does.
function record(cwd, summary, opts = {}) {
  const appended = appendUsage(cwd, entryFromSummary(summary, opts.now));
  const wantCommit = opts.commit !== false;
  const commit = wantCommit ? commitUsage(cwd, summary.runId) : { committed: false };
  return {
    path: appended.path,
    row: appended.row,
    committed: commit.committed,
    commitError: commit.error || null,
  };
}

// --- read / rollup (the CLI and the §4.1 daily-limit check) -------------------

// Parse usage.csv → { rows, skipped }. Missing file → empty ledger. Each
// malformed line is skipped and reported via opts.warn(message) (default:
// silent collection — the count is always in `skipped`).
function readUsage(cwd, opts = {}) {
  const warn = opts.warn || (() => {});
  const file = usagePath(cwd);
  if (!fs.existsSync(file)) {
    return { path: file, exists: false, rows: [], skipped: 0 };
  }
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  const rows = [];
  let skipped = 0;
  let sawHeader = false;
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.trim() === '') {
      continue;
    }
    if (line === HEADER) {
      sawHeader = true; // header row (required on line 1; tolerated if repeated)
      continue;
    }
    if (i === 0) {
      warn(`usage.csv line 1: expected header '${HEADER}' — parsing rows anyway`);
    }
    const cells = splitCsvLine(line);
    if (cells === null || cells.length !== COLUMNS.length) {
      skipped += 1;
      warn(`usage.csv line ${i + 1}: malformed row skipped`);
      continue;
    }
    const row = {};
    for (let c = 0; c < COLUMNS.length; c += 1) {
      row[COLUMNS[c]] = cells[c];
    }
    const ts = Date.parse(row.timestamp);
    const tokensIn = Number(row.tokens_in);
    const tokensOut = Number(row.tokens_out);
    const estUsd = row.est_usd === '' ? 0 : Number(row.est_usd);
    const wallSecs = Number(row.wall_secs);
    if (
      Number.isNaN(ts) ||
      !Number.isFinite(tokensIn) ||
      !Number.isFinite(tokensOut) ||
      !Number.isFinite(estUsd) ||
      !Number.isFinite(wallSecs)
    ) {
      skipped += 1;
      warn(`usage.csv line ${i + 1}: malformed row skipped`);
      continue;
    }
    rows.push({
      timestamp: row.timestamp,
      ts,
      run_id: row.run_id,
      repo: row.repo,
      roles: row.roles === '' ? [] : row.roles.split('+'),
      tokens_in: tokensIn,
      tokens_out: tokensOut,
      est_usd: estUsd,
      wall_secs: wallSecs,
      outcome: row.outcome,
    });
  }
  if (!sawHeader && rows.length === 0 && skipped === 0) {
    warn('usage.csv: empty file without header — treating as empty ledger');
  }
  return { path: file, exists: true, rows, skipped };
}

function startOfUtcDay(date) {
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
}

function rollup(rows) {
  const totals = { runs: 0, tokens_in: 0, tokens_out: 0, est_usd: 0, outcomes: {} };
  for (const r of rows) {
    totals.runs += 1;
    totals.tokens_in += r.tokens_in;
    totals.tokens_out += r.tokens_out;
    totals.est_usd += r.est_usd;
    totals.outcomes[r.outcome] = (totals.outcomes[r.outcome] || 0) + 1;
  }
  totals.est_usd = Number(totals.est_usd.toFixed(4)); // keep float noise out of output
  return totals;
}

// Totals over the last `days` UTC calendar days including today (UTC).
function summarizeUsage(cwd, opts = {}) {
  const days = opts.days ?? 7;
  if (!Number.isInteger(days) || days < 1) {
    throw new Error(`--days must be a positive integer, got ${JSON.stringify(opts.days)}`);
  }
  const now = opts.now || new Date();
  const since = startOfUtcDay(now) - (days - 1) * 86_400_000;
  const ledger = readUsage(cwd, opts);
  const totals = rollup(ledger.rows.filter((r) => r.ts >= since));
  return {
    days,
    since: new Date(since).toISOString(),
    timezone: 'UTC',
    ...totals,
    skipped_rows: ledger.skipped,
    path: ledger.path,
  };
}

// "Today" (UTC) totals — what the worker's §4.1 daily-limit startup check sums.
function todayTotals(cwd, opts = {}) {
  return summarizeUsage(cwd, { ...opts, days: 1 });
}

// §4.1 startup check: daily limits not already exceeded. Returns
// { ok: true, totals } or { ok: false, slug: 'daily-limit', message, totals }
// for the worker to turn into `verity-worker: 30 daily-limit: <message>`.
// T12's remaining startup checks can reuse this as-is.
function checkDailyLimits(cwd, limits, opts = {}) {
  const totals = todayTotals(cwd, opts);
  if (typeof limits.max_usd_per_day === 'number' && totals.est_usd >= limits.max_usd_per_day) {
    return {
      ok: false,
      slug: 'daily-limit',
      message: `daily budget reached: est $${totals.est_usd.toFixed(2)} spent today (UTC) >= max_usd_per_day ${limits.max_usd_per_day}`,
      totals,
    };
  }
  if (Number.isInteger(limits.max_runs_per_day) && totals.runs >= limits.max_runs_per_day) {
    return {
      ok: false,
      slug: 'daily-limit',
      message: `daily run cap reached: ${totals.runs} runs today (UTC) >= max_runs_per_day ${limits.max_runs_per_day}`,
      totals,
    };
  }
  return { ok: true, totals };
}

// --- CLI: `verity usage [--days 7] [--json]` (§3.4) ---------------------------

function dispatch(args, flags) {
  if (args.length > 0) {
    throw new Error('usage takes no positional arguments — verity usage [--days 7] [--json]');
  }
  const cwd = flags.cwd || process.cwd();
  let days = 7;
  if (flags.days !== undefined) {
    days = Number(flags.days);
    if (!Number.isInteger(days) || days < 1) {
      throw new Error(`--days must be a positive integer, got '${flags.days}'`);
    }
  }
  // Warnings go to stderr so `usage --json` stdout stays exactly one object.
  const summary = summarizeUsage(cwd, {
    days,
    warn: (msg) => process.stderr.write(`verity usage: warn: ${msg}\n`),
  });
  if (flags.json) {
    return summary; // --json: exactly the totals object, no presentation extras
  }
  return {
    ...summary,
    raw: `runs=${summary.runs} tokens_in=${summary.tokens_in} tokens_out=${summary.tokens_out} est_usd=${summary.est_usd.toFixed(2)} days=${summary.days}`,
  };
}

module.exports = {
  COLUMNS,
  CSV_REL_PATH,
  HEADER,
  appendUsage,
  checkDailyLimits,
  commitUsage,
  dispatch,
  entryFromSummary,
  formatRow,
  readUsage,
  record,
  rollup,
  splitCsvLine,
  summarizeUsage,
  todayTotals,
  usagePath,
};
