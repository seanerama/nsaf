// `verity agent-exec <role> [args...]` — headless single-role execution
// (verity-autonomy-technical-sketch.md §3.3). The ONLY place that invokes an
// AI assistant.
//
//   verity agent-exec build 7 --run-id <id> [--max-turns N] [--agent claude|opencode]
//
// Flow:
//   1. Resolve role → commands/verity/<role>.md prompt file + its REQUIRED
//      <role>.tools.json allowlist (T06, deny-by-default): a missing allowlist
//      means the agent is never invoked — exit 30 with a single-line error
//      naming the missing file. No role runs with the agent's default tools.
//   2. Fail fast (exit 30) if the agent binary is missing or below the pinned
//      minimum version (package.json `verity.claudeCodeMinVersion`).
//   3. Invoke `claude -p "<rendered prompt>" --output-format stream-json
//      --verbose --max-turns N [--allowed-tools <each entry verbatim>]` with
//      cwd = repo root. Flag spellings verified against Claude Code 2.1.170 —
//      see docs/dev/autonomy-pathmap.md "Claude Code headless interface".
//      stream-json (not json) is a deliberate deviation: one invocation streams
//      the raw transcript AND ends with the same `type:"result"` object.
//   4. Transcript streams kernel-side to ~/.verity/logs/<run-id>/<role>.jsonl
//      ($HOME-relative via os.homedir(), so tests can redirect it).
//   5. Parse the final result line for outcome + usage; emit the §3.3 result
//      object on stdout:
//        { schema, role, outcome, tokens:{in,out}, est_usd, wall_secs,
//          artifacts, error }
//
// Outcome detection: every rendered prompt gets a RESULT_CONTRACT footer telling
// the (human-less) agent to end its final message with one single-line JSON
// marker {"verity":1,"outcome":"success|gated|failed",...}. Marker wins; no
// marker → infer from the CLI result (is_error:false/subtype:success → success,
// else failed). No parseable result object at all → infra_error.
//
// Exit codes (mapped by exitCodeFor() in the dispatcher): 0 success, 10 gated,
// 20 role failure, 30 infra (agent missing/too old, unsupported agent, unknown
// role, malformed output). Infra outcomes also print one machine-parsable line
// to stderr: `verity-agent-exec: 30 <slug>: <message>` (SKETCH §8.2 style).
//
// Test seam: the agent binary is overridable via VERITY_AGENT_BIN — tests use a
// stub script emitting canned JSONL; no live API calls ever happen in CI.
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PKG = require('../../../package.json');

const SCHEMA = 1;
const DEFAULT_AGENT = 'claude';
const DEFAULT_MAX_TURNS = 40;
const MIN_CLAUDE_VERSION = PKG.verity?.claudeCodeMinVersion || '2.1.170';
// run-id and role become path components under ~/.verity/logs — keep them tame.
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const OUTCOMES = ['success', 'gated', 'failed'];
const USAGE =
  'usage: verity agent-exec <role> [args...] --run-id <id> [--max-turns N] [--agent claude|opencode]';

// Appended to every rendered role prompt: how a headless role reports back.
const RESULT_CONTRACT = `
<headless-result-contract>
You are running headless under \`verity agent-exec\` — no human is present.
Never wait for user input or ask questions. If progress requires a human
decision, approval, or gate, stop working and report the outcome "gated".
The very LAST line of your final message MUST be exactly one single-line JSON
object (no code fence on that line), shaped like:
{"verity":1,"outcome":"success","gate":null,"artifacts":{"pr":114,"issues":[98]},"reason":"one line"}
- outcome "success": the role's goal is fully done.
- outcome "gated": a human gate/approval/decision blocks further progress
  (set "gate" to the gate name, e.g. "review:merge").
- outcome "failed": you could not complete the role's goal (set "reason").
"artifacts" lists GitHub objects you created/updated (best effort).
</headless-result-contract>
`;

class AgentExecError extends Error {
  constructor(message, slug) {
    super(message);
    this.name = 'AgentExecError';
    this.exitCode = 30;
    this.slug = slug || null;
  }
}

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function firstLine(text) {
  return String(text || '')
    .split('\n')
    .find((l) => l.trim().length > 0);
}

// "2.1.170 (Claude Code)" → [2, 1, 170]; null when no x.y.z is present.
function parseVersion(text) {
  const m = /(\d+)\.(\d+)\.(\d+)/.exec(String(text || ''));
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

function compareVersions(a, b) {
  for (let i = 0; i < 3; i += 1) {
    if (a[i] !== b[i]) {
      return a[i] < b[i] ? -1 : 1;
    }
  }
  return 0;
}

// Fail-fast min-version check (SKETCH §3.3): missing binary or version below
// the pin → { ok:false, slug, error }; never throws.
function checkAgentVersion(bin, opts = {}) {
  const exec = opts.exec || spawnSync;
  const res = exec(bin, ['--version'], { encoding: 'utf8' });
  if (res.error || res.status !== 0) {
    const why = res.error ? res.error.code || res.error.message : `exit ${res.status}`;
    return {
      ok: false,
      slug: 'agent-missing',
      error: `agent binary not runnable: ${bin} (${why})`,
    };
  }
  const found = parseVersion(res.stdout);
  if (!found) {
    return {
      ok: false,
      slug: 'agent-missing',
      error: `could not parse \`${bin} --version\` output: ${firstLine(res.stdout) || '(empty)'}`,
    };
  }
  const version = found.join('.');
  if (compareVersions(found, parseVersion(MIN_CLAUDE_VERSION)) < 0) {
    return {
      ok: false,
      slug: 'version-too-old',
      error: `Claude Code ${version} is below the pinned minimum ${MIN_CLAUDE_VERSION} — run \`claude update\``,
    };
  }
  return { ok: true, version };
}

// Role → command file + allowlist file, preferring the target repo's installed
// copies over the packaged ones. Returns null when the role does not exist.
function resolveRole(cwd, role) {
  const dirs = [
    path.join(cwd, 'commands', 'verity'),
    path.join(cwd, '.claude', 'commands', 'verity'),
    path.join(__dirname, '..', '..', '..', 'commands', 'verity'),
  ];
  for (const dir of dirs) {
    const file = path.join(dir, `${role}.md`);
    if (fs.existsSync(file)) {
      return { file, toolsFile: path.join(dir, `${role}.tools.json`) };
    }
  }
  return null;
}

// T06: <role>.tools.json = non-empty JSON array of tool-permission strings
// (SKETCH §5 matrix), passed verbatim to the agent CLI after --allowed-tools.
// Deny-by-default: a MISSING allowlist does NOT fall back to the agent's
// default tool set — agent-exec refuses to invoke the agent at all (exit 30).
// Empty arrays are rejected too: "allow nothing" must be impossible to confuse
// with "forgot the file" / "flag omitted".
function readAllowlist(toolsFile) {
  if (!fs.existsSync(toolsFile)) {
    throw new AgentExecError(
      `deny-all: missing tool allowlist ${toolsFile} — every role needs a <role>.tools.json next to its command file (SKETCH §5)`,
      'missing-allowlist',
    );
  }
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(toolsFile, 'utf8'));
  } catch (err) {
    throw new AgentExecError(`invalid allowlist ${toolsFile}: ${err.message}`);
  }
  if (!Array.isArray(parsed) || parsed.length === 0 || parsed.some((t) => typeof t !== 'string')) {
    throw new AgentExecError(
      `invalid allowlist ${toolsFile}: must be a non-empty JSON array of strings`,
    );
  }
  return parsed;
}

// Render the role command file the way Claude Code would run it as a slash
// command: strip the YAML frontmatter, substitute $ARGUMENTS (the only
// placeholder the 13 role files use), then append the headless result contract.
function renderPrompt(file, roleArgs) {
  let text = fs.readFileSync(file, 'utf8');
  text = text.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  text = text.replace(/\$ARGUMENTS/g, roleArgs.join(' '));
  return `${text.trimEnd()}\n${RESULT_CONTRACT}`;
}

// Last line of the role's final message that parses as the outcome marker.
function extractMarker(text) {
  const lines = String(text || '').split('\n');
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const t = lines[i].trim();
    if (!t.startsWith('{') || !t.endsWith('}')) {
      continue;
    }
    try {
      const obj = JSON.parse(t);
      if (isPlainObject(obj) && OUTCOMES.includes(obj.outcome)) {
        return obj;
      }
    } catch {
      // not JSON — keep scanning upward
    }
  }
  return null;
}

// Last transcript line that is the agent CLI's final result object.
function lastResultLine(transcriptPath) {
  let raw;
  try {
    raw = fs.readFileSync(transcriptPath, 'utf8');
  } catch {
    return null;
  }
  const lines = raw.split('\n');
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const t = lines[i].trim();
    if (t === '') {
      continue;
    }
    try {
      const obj = JSON.parse(t);
      if (isPlainObject(obj) && obj.type === 'result') {
        return obj;
      }
    } catch {
      // non-JSON noise — keep scanning upward
    }
  }
  return null;
}

function exitCodeFor(result) {
  const map = { success: 0, gated: 10, failed: 20, infra_error: 30 };
  const code = map[result?.outcome];
  return code === undefined ? 30 : code;
}

function dispatch(args, flags) {
  const cwd = flags.cwd || process.cwd();
  const t0 = Date.now();
  const stderr = (line) => process.stderr.write(`${line}\n`);

  // §3.3 result object, exact field set — infra problems still emit it (with
  // outcome infra_error) so callers (T10) always get one parseable object.
  const result = (outcome, extra = {}) => ({
    schema: SCHEMA,
    role: args[0] || null,
    outcome,
    tokens: { in: 0, out: 0 },
    est_usd: null,
    wall_secs: Math.round((Date.now() - t0) / 1000),
    artifacts: {},
    error: null,
    ...extra,
  });
  const infra = (slug, message) => {
    stderr(`verity-agent-exec: 30 ${slug}: ${message}`);
    return result('infra_error', { error: message });
  };

  // -- argument validation (true usage errors throw → dispatcher exits 30) --
  const role = args[0];
  if (!role) {
    throw new AgentExecError(USAGE);
  }
  const roleArgs = args.slice(1);
  const runId = flags['run-id'];
  if (typeof runId !== 'string' || !SAFE_ID.test(runId)) {
    throw new AgentExecError(`--run-id is required (letters/digits/._- only). ${USAGE}`);
  }
  const rawTurns = flags['max-turns'] === undefined ? DEFAULT_MAX_TURNS : flags['max-turns'];
  const maxTurns = Number(rawTurns);
  if (rawTurns === true || !Number.isInteger(maxTurns) || maxTurns < 1) {
    throw new AgentExecError(`--max-turns must be a positive integer. ${USAGE}`);
  }

  // -- infra preconditions (emit infra_error result, exit 30) --
  const agent = flags.agent === undefined ? DEFAULT_AGENT : String(flags.agent);
  if (agent !== 'claude') {
    return infra(
      'unsupported-agent',
      `unsupported agent '${agent}' — only 'claude' is implemented (opencode is T18)`,
    );
  }
  if (!SAFE_ID.test(role)) {
    return infra('unknown-role', `invalid role name '${role}'`);
  }
  const resolved = resolveRole(cwd, role);
  if (resolved === null) {
    return infra('unknown-role', `no command file for role '${role}' (commands/verity/${role}.md)`);
  }
  const bin = process.env.VERITY_AGENT_BIN || 'claude';
  const version = checkAgentVersion(bin);
  if (!version.ok) {
    return infra(version.slug, version.error);
  }
  let allowlist;
  try {
    allowlist = readAllowlist(resolved.toolsFile);
  } catch (err) {
    return infra(err.slug || 'bad-allowlist', err.message);
  }

  // -- invocation --
  const prompt = renderPrompt(resolved.file, roleArgs);
  const argv = [
    '-p',
    prompt,
    '--output-format',
    'stream-json',
    '--verbose',
    '--max-turns',
    String(maxTurns),
  ];
  // Always present (readAllowlist guarantees a non-empty list). Variadic flag
  // last so it can't swallow other args; entries verbatim (T06).
  argv.push('--allowed-tools', ...allowlist);

  const logDir = path.join(os.homedir(), '.verity', 'logs', runId);
  fs.mkdirSync(logDir, { recursive: true });
  const transcript = path.join(logDir, `${role}.jsonl`);

  // stdout goes straight to the transcript file (true streaming — the kernel
  // writes as the agent emits, even though this CLI is synchronous).
  const fd = fs.openSync(transcript, 'w');
  let run;
  try {
    run = spawnSync(bin, argv, {
      cwd,
      stdio: ['ignore', fd, 'pipe'],
      encoding: 'utf8',
      maxBuffer: 16 * 1024 * 1024,
    });
  } finally {
    fs.closeSync(fd);
  }
  if (run.error) {
    return infra('spawn-failed', `failed to run ${bin}: ${run.error.message}`);
  }

  // -- result parsing --
  const final = lastResultLine(transcript);
  if (final === null) {
    const hint = firstLine(run.stderr) || `agent exit ${run.status}`;
    return infra(
      'malformed-output',
      `agent emitted no parseable result object (${hint}); transcript: ${transcript}`,
    );
  }
  const usage = isPlainObject(final.usage) ? final.usage : {};
  const tokens = {
    in:
      (usage.input_tokens || 0) +
      (usage.cache_creation_input_tokens || 0) +
      (usage.cache_read_input_tokens || 0),
    out: usage.output_tokens || 0,
  };
  const estUsd = typeof final.total_cost_usd === 'number' ? final.total_cost_usd : null;

  const marker = extractMarker(final.result);
  let outcome;
  let error = null;
  let artifacts = {};
  if (marker !== null) {
    outcome = marker.outcome;
    artifacts = isPlainObject(marker.artifacts) ? marker.artifacts : {};
    if (outcome === 'failed') {
      error = typeof marker.reason === 'string' ? marker.reason : 'role reported failure';
    }
  } else if (final.is_error === false && final.subtype === 'success') {
    outcome = 'success';
  } else {
    outcome = 'failed';
    error =
      final.subtype === 'error_max_turns'
        ? `max turns (${maxTurns}) exhausted`
        : firstLine(final.result) || `agent error (${final.subtype || 'unknown'})`;
  }
  return result(outcome, { tokens, est_usd: estUsd, artifacts, error });
}

module.exports = {
  AgentExecError,
  DEFAULT_MAX_TURNS,
  MIN_CLAUDE_VERSION,
  RESULT_CONTRACT,
  SCHEMA,
  checkAgentVersion,
  compareVersions,
  dispatch,
  exitCodeFor,
  extractMarker,
  parseVersion,
  readAllowlist,
  renderPrompt,
  resolveRole,
};
