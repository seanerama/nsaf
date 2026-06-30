// Verity adapter / installer — the Runtime Adapter layer (framework-spec.md §4b).
// Same role-command CONTENT, transformed into each harness's format + install
// location. Claude Code is the reference harness; OpenCode is the second adapter.
// Capability differences (no Task sub-agents / no hooks on OpenCode) are handled by
// the commands' own "implement inline" fallback — the content already degrades.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const deployment = require('./deployment.cjs');
const labels = require('./labels.cjs');

const PKG_ROOT = path.join(__dirname, '..', '..', '..');

// Part of setup: seed the user-global deployment-methods catalog (NEVER clobbered).
// It lives in the user's home (~/.verity), independent of the harness target dir.
function seedDeploymentMethods(opts) {
  const seed = deployment.ensure({ home: opts.home });
  return { ...seed, label: `${seed.path}${seed.created ? '' : ' (existing)'}` };
}

function commandFiles(srcCommands, ext = '.md') {
  return fs.readdirSync(srcCommands).filter((n) => n.endsWith(ext));
}

function copyInternals(target) {
  fs.cpSync(path.join(PKG_ROOT, 'verity'), path.join(target, 'verity'), { recursive: true });
}

function claudeDir(opts) {
  return opts.target || process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
}

function installClaude(opts = {}) {
  const target = claudeDir(opts);
  const installed = [];

  // 1. Role command files + their T06 tool allowlists (<role>.tools.json) →
  //    <target>/commands/verity/. agent-exec resolves both from the SAME dir,
  //    and a missing allowlist is deny-all (exit 30) — so the installed copies
  //    must always travel together.
  const srcCommands = path.join(PKG_ROOT, 'commands', 'verity');
  const destCommands = path.join(target, 'commands', 'verity');
  fs.mkdirSync(destCommands, { recursive: true });
  for (const name of [...commandFiles(srcCommands), ...commandFiles(srcCommands, '.tools.json')]) {
    fs.copyFileSync(path.join(srcCommands, name), path.join(destCommands, name));
    installed.push(path.join('commands', 'verity', name));
  }

  // 2. Engine internals → <target>/verity/ (self-contained fallback for the CLI)
  copyInternals(target);
  installed.push('verity/');

  // 3. Seed the global deployment-methods catalog (setup step).
  const deploymentMethods = seedDeploymentMethods(opts);
  installed.push(deploymentMethods.label);

  return { harness: 'claude', target, installed, deploymentMethods };
}

// --- OpenCode adapter ---

function openCodeDir(opts) {
  return (
    opts.target || process.env.OPENCODE_CONFIG_DIR || path.join(os.homedir(), '.config', 'opencode')
  );
}

// Transform a Claude command .md into OpenCode's command format:
// - frontmatter reduced to `description:` (OpenCode's per-command field; the
//   Claude-only `allowed-tools` allowlist + `name` are dropped — OpenCode manages
//   permissions globally and derives the command id from the filename)
// - the Claude-specific CLI fallback path is rewritten to the OpenCode config dir
function transformForOpenCode(content) {
  const m = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!m) {
    return content;
  }
  const description = (m[1].match(/^description:\s*(.+)$/m) || [])[1] || '';
  const body = m[2].replace(
    /\$HOME\/\.claude\/verity/g,
    '${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}/verity',
  );
  return `---\ndescription: ${description}\n---\n${body}`;
}

function installOpenCode(opts = {}) {
  const target = openCodeDir(opts);
  const installed = [];

  // Role commands → <target>/command/, flattened to verity-<name>.md (invoked /verity-<name>)
  const srcCommands = path.join(PKG_ROOT, 'commands', 'verity');
  const destCommands = path.join(target, 'command');
  fs.mkdirSync(destCommands, { recursive: true });
  for (const name of commandFiles(srcCommands)) {
    const out = `verity-${name}`;
    const transformed = transformForOpenCode(fs.readFileSync(path.join(srcCommands, name), 'utf8'));
    fs.writeFileSync(path.join(destCommands, out), transformed);
    installed.push(path.join('command', out));
  }

  copyInternals(target);
  installed.push('verity/');

  const deploymentMethods = seedDeploymentMethods(opts);
  installed.push(deploymentMethods.label);

  return { harness: 'opencode', target, installed, deploymentMethods };
}

// --- GitHub Actions driver (T15) ---
//
// `verity install --actions` scaffolds .github/workflows/verity-worker.yml from
// the SKETCH §6 template. Bot login: default 'verity-bot' (the §6 literal),
// override with `--bot <login>` — it only parameterizes the self-event guard
// (`github.actor != '<bot>'`), so a wrong value fails safe (extra runs that the
// worker's own §4.2 no-self-feeding rule then ignores), never silently skips
// human events. Not read from .verity/autonomy.yml: the policy has no bot field
// (the bot is whoever owns VERITY_BOT_TOKEN, known only at secret-config time).
const ACTIONS_WORKFLOW_PATH = path.join('.github', 'workflows', 'verity-worker.yml');
const ACTIONS_DEFAULT_BOT = 'verity-bot';

// How the headless agent authenticates to Anthropic. `api-key` is the default
// (pay-per-token, no usage ceiling). `subscription` runs `claude -p` against a
// Claude Pro/Max plan via an OAuth token from `claude setup-token` — usage draws
// from the plan's monthly Agent SDK credit and STOPS when that's exhausted.
const ACTIONS_DEFAULT_AUTH = 'api-key';
const ACTIONS_AUTH_MODES = ['api-key', 'subscription'];

// The two agent-auth variants: the header doc lines + the worker-step env entry.
// api-key MUST stay byte-identical to the original §6 template (frozen fixture).
function agentAuthBlock(auth) {
  if (auth === 'subscription') {
    return {
      headerDoc: [
        '#   CLAUDE_CODE_OAUTH_TOKEN — subscription auth for the headless agent. Generate it once',
        "#                        with 'claude setup-token' (≈1-year token) on a machine logged",
        '#                        into your Claude Pro/Max plan, then store it here. Headless',
        "#                        'claude -p' usage draws from your plan's monthly Agent SDK credit;",
        '#                        when that credit is exhausted the worker STOPS until the next',
        '#                        cycle — it does NOT fall back to paid API billing.',
        '#                        Do NOT also set ANTHROPIC_API_KEY: an API key takes precedence',
        '#                        and would force pay-per-token billing instead of the subscription.',
      ].join('\n'),
      env: 'CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}',
    };
  }
  return {
    headerDoc: [
      '#   ANTHROPIC_API_KEY  — API key for the headless agent (verity agent-exec).',
      '#                        This is the key that spends money — see guardrails.',
    ].join('\n'),
    env: 'ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}',
  };
}

// SKETCH §6 template, frozen contract. Deliberate adjustments, documented:
//   - block-style YAML (the sketch's flow-style `issue_comment:{...}` is not
//     even valid YAML; actionlint-verified spelling below),
//   - setup-node WITHOUT `cache: npm` — the cache option hard-fails when the
//     target repo has no npm lockfile (most Verity-managed repos aren't npm
//     projects), and the only npm work here is a global install of the tools.
function actionsWorkflowYaml(bot = ACTIONS_DEFAULT_BOT, opts = {}) {
  if (!/^[A-Za-z0-9-]+(\[bot\])?$/.test(bot)) {
    throw new Error(`invalid bot login for --bot: ${JSON.stringify(bot)}`);
  }
  const auth = opts.auth || ACTIONS_DEFAULT_AUTH;
  if (!ACTIONS_AUTH_MODES.includes(auth)) {
    throw new Error(
      `invalid --auth (use ${ACTIONS_AUTH_MODES.join(' | ')}): ${JSON.stringify(auth)}`,
    );
  }
  const agentAuth = agentAuthBlock(auth);
  return `# verity-worker — GitHub Actions driver for Verity autonomy.
# Generated by \`verity install --actions\` (bot login: ${bot}).
# Regenerate with the same command; it refuses to overwrite local edits
# unless you pass --force.
#
# Required repository secrets (Settings → Secrets and variables → Actions):
#   VERITY_BOT_TOKEN   — token for the DEDICATED bot machine account. Used for
#                        checkout and every gh call so all worker actions stay
#                        bot-attributed, AND to install verity-auto from GitHub
#                        (the install step below). It therefore needs WRITE
#                        access to this repo + READ access to seanerama/verity-auto.
#                        Never a human's token: the worker refuses to start
#                        (exit 30 bot-is-human) if its login is listed under \`humans:\`.
${agentAuth.headerDoc}
#
# Budget guardrails (ON by default):
#   - timeout-minutes: 50 hard-caps any single run at the Actions level.
#   - the worker's startup checks refuse to run (exit 30 daily-limit) once
#     today's .verity/usage.csv totals exceed limits.max_usd_per_day or
#     limits.max_runs_per_day from .verity/autonomy.yml.
#   - the concurrency group serializes runs: when the 30-minute schedule and
#     an event fire together (or a cron driver also ticks the same repo),
#     GitHub queues instead of double-working — and the worker's GitHub lock
#     protocol is the second fence.
#   - the \`github.actor != '${bot}'\` guard stops the bot's own labels,
#     comments and pushes from re-triggering this workflow (self-event loop).
name: verity-worker
on:
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened, labeled, synchronize]
  issue_comment:
    types: [created] # an approval comment wakes the worker (see docs/autonomy.md)
  schedule:
    - cron: '*/30 * * * *'
concurrency:
  group: verity-\${{ github.repository }}
  cancel-in-progress: false
jobs:
  work:
    if: github.actor != '${bot}' # self-event guard (templated login)
    runs-on: ubuntu-latest
    timeout-minutes: 50
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: \${{ secrets.VERITY_BOT_TOKEN }}
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm i -g "git+https://x-access-token:\${VERITY_BOT_TOKEN}@github.com/seanerama/verity-auto.git" @anthropic-ai/claude-code
        env:
          VERITY_BOT_TOKEN: \${{ secrets.VERITY_BOT_TOKEN }}
      - run: verity-worker --repo \${{ github.repository }} --once
        env:
          GH_TOKEN: \${{ secrets.VERITY_BOT_TOKEN }}
          ${agentAuth.env}
`;
}

// Idempotent scaffold. Same inputs twice → byte-identical file, reported
// `unchanged`. A file that differs from what we would generate (local edits,
// or a different --bot) is NEVER clobbered silently: hard error naming
// --force; `--force` regenerates and reports `updated`.
function installActions(opts = {}) {
  const cwd = opts.cwd || process.cwd();
  const bot = typeof opts.bot === 'string' ? opts.bot : ACTIONS_DEFAULT_BOT;
  const auth = typeof opts.auth === 'string' ? opts.auth : ACTIONS_DEFAULT_AUTH;
  const content = actionsWorkflowYaml(bot, { auth });
  const file = path.join(cwd, ACTIONS_WORKFLOW_PATH);
  if (fs.existsSync(file)) {
    if (fs.readFileSync(file, 'utf8') === content) {
      return {
        harness: 'actions',
        path: ACTIONS_WORKFLOW_PATH,
        bot,
        auth,
        created: false,
        unchanged: true,
      };
    }
    if (!opts.force) {
      throw new Error(
        `${ACTIONS_WORKFLOW_PATH} exists with different content (local edits, a different --bot login, or a different --auth mode) — refusing to overwrite. Re-run with --force to regenerate.`,
      );
    }
    fs.writeFileSync(file, content);
    return {
      harness: 'actions',
      path: ACTIONS_WORKFLOW_PATH,
      bot,
      auth,
      created: false,
      updated: true,
    };
  }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
  return { harness: 'actions', path: ACTIONS_WORKFLOW_PATH, bot, auth, created: true };
}

function dispatch(_args, flags) {
  let result;
  if (flags.actions) {
    // Standalone scaffold into the TARGET REPO (cwd), not a harness config dir.
    // Run plain `verity install` separately for commands/labels.
    result = installActions({
      cwd: flags.cwd,
      bot: flags.bot,
      auth: flags.auth,
      force: Boolean(flags.force),
    });
    result.labels = labels.ensureLabels(flags.cwd || process.cwd());
    return result;
  }
  if (flags.opencode) {
    result = installOpenCode({ target: flags.target, home: flags.home });
  } else if (flags.codex || flags.gemini) {
    throw new Error('only the claude and opencode adapters are implemented so far');
  } else {
    result = installClaude({ target: flags.target, home: flags.home });
  }
  // Autonomy label vocabulary on the target repo (SKETCH §1): idempotent
  // create-or-update, never delete. Best-effort — offline / outside a repo,
  // install still succeeds and the labels step reports itself as skipped.
  result.labels = labels.ensureLabels(flags.cwd || process.cwd());
  return result;
}

module.exports = {
  installClaude,
  installActions,
  actionsWorkflowYaml,
  ACTIONS_WORKFLOW_PATH,
  ACTIONS_DEFAULT_BOT,
  ACTIONS_DEFAULT_AUTH,
  ACTIONS_AUTH_MODES,
  installOpenCode,
  transformForOpenCode,
  openCodeDir,
  dispatch,
  claudeDir,
  PKG_ROOT,
};
