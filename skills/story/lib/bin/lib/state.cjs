'use strict';

const fs = require('fs');
const path = require('path');
const { getOutputDir, safeReadFile, currentTimestamp, output, error } = require('./core.cjs');
const { STAGES, STAGE_SEQUENCE, getStage } = require('./stages.cjs');

// ─── Frontmatter Parsing ─────────────────────────────────────────────────────

function extractFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return {};
  const obj = {};
  const lines = match[1].split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const kv = line.match(/^(\w[\w_]*):\s*(.*)/);
    if (kv) {
      const key = kv[1];
      let val = kv[2].trim();
      // Nested object
      if (val === '') {
        const nested = {};
        i++;
        while (i < lines.length && lines[i].match(/^\s{2}\w/)) {
          const nkv = lines[i].match(/^\s{2}(\w[\w_]*):\s*(.*)/);
          if (nkv) nested[nkv[1]] = coerce(nkv[2].trim());
          i++;
        }
        obj[key] = nested;
        continue;
      }
      // Array
      if (val.startsWith('[')) {
        try { obj[key] = JSON.parse(val); } catch { obj[key] = val; }
      } else {
        obj[key] = coerce(val);
      }
    }
    i++;
  }
  return obj;
}

function coerce(val) {
  if (val === 'true') return true;
  if (val === 'false') return false;
  if (/^\d+$/.test(val)) return parseInt(val, 10);
  return val.replace(/^["']|["']$/g, '');
}

function reconstructFrontmatter(obj) {
  const lines = ['---'];
  for (const [key, val] of Object.entries(obj)) {
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      lines.push(`${key}:`);
      for (const [nk, nv] of Object.entries(val)) {
        lines.push(`  ${nk}: ${formatVal(nv)}`);
      }
    } else if (Array.isArray(val)) {
      lines.push(`${key}: ${JSON.stringify(val)}`);
    } else {
      lines.push(`${key}: ${formatVal(val)}`);
    }
  }
  lines.push('---');
  return lines.join('\n');
}

function formatVal(v) {
  if (typeof v === 'string') return `"${v}"`;
  return String(v);
}

function stripFrontmatter(content) {
  return content.replace(/^---\n[\s\S]*?\n---\n*/, '');
}

// ─── State Sync ──────────────────────────────────────────────────────────────

function buildStateFrontmatter(body) {
  const fm = {
    story_state_version: '1.0',
  };

  // Extract status
  const statusMatch = body.match(/\*\*Status:\*\*\s*(.+)/i);
  fm.status = statusMatch ? statusMatch[1].trim().toLowerCase() : 'not_started';

  // Extract completed stages from checklist
  const completedMatches = body.matchAll(/- \[x\] (.+?)(?:\s*—|\s*$)/gm);
  fm.completed_stages = [];
  for (const m of completedMatches) {
    const name = m[1].trim();
    const stage = Object.values(STAGES).find(s => s.name === name);
    if (stage) fm.completed_stages.push(stage.id);
  }

  // Extract active stages
  const activeSection = body.match(/## Active Stages?\s*\n([\s\S]*?)(?=\n##|$)/);
  fm.active_stages = [];
  if (activeSection) {
    const actives = activeSection[1].matchAll(/\*\*(.+?):\*\*/g);
    for (const m of actives) {
      const name = m[1].trim();
      const stage = Object.values(STAGES).find(s => s.name === name);
      if (stage) fm.active_stages.push(stage.id);
    }
  }

  // Progress
  const total = STAGE_SEQUENCE.length;
  const completed = fm.completed_stages.length;
  fm.progress = {
    total_stages: total,
    completed_stages: completed,
    percent: total > 0 ? Math.round((completed / total) * 100) : 0,
  };

  fm.last_updated = currentTimestamp();

  return fm;
}

function syncAndWrite(statePath, content) {
  const body = stripFrontmatter(content);
  const fm = buildStateFrontmatter(body);
  const full = reconstructFrontmatter(fm) + '\n\n' + body.replace(/^\n+/, '');
  fs.writeFileSync(statePath, full);
  return fm;
}

// ─── Field Operations ────────────────────────────────────────────────────────

function stateReplaceField(content, fieldName, newValue) {
  const regex = new RegExp(`(\\*\\*${fieldName}:\\*\\*\\s*)(.+)`, 'i');
  if (!regex.test(content)) return null;
  return content.replace(regex, `$1${newValue}`);
}

// ─── CLI Commands ────────────────────────────────────────────────────────────

function cmdStateLoad(cwd, raw) {
  const dir = getOutputDir(cwd);
  const statePath = path.join(dir, 'STATE.md');
  const configPath = path.join(dir, 'config.json');
  const result = {
    state_exists: fs.existsSync(statePath),
    config_exists: fs.existsSync(configPath),
    output_dir: dir,
  };
  if (result.config_exists) {
    try { result.config = JSON.parse(fs.readFileSync(configPath, 'utf8')); } catch { result.config = null; }
  }
  output(result, raw);
}

function cmdStateJson(cwd, raw) {
  const statePath = path.join(getOutputDir(cwd), 'STATE.md');
  const content = safeReadFile(statePath);
  if (!content) error('STATE.md not found');
  const fm = extractFrontmatter(content);
  output(fm, raw);
}

function cmdStateStartStage(cwd, stageId, raw) {
  const stage = getStage(stageId);
  if (!stage) error(`Unknown stage: ${stageId}`);

  const statePath = path.join(getOutputDir(cwd), 'STATE.md');
  let content = safeReadFile(statePath);
  if (!content) error('STATE.md not found');

  // Update status to in progress
  content = stateReplaceField(content, 'Status', 'In Progress') || content;

  // Add to Active Stages section
  const activeMarker = '## Active Stages';
  const idx = content.indexOf(activeMarker);
  if (idx !== -1) {
    const insertPos = idx + activeMarker.length;
    const nextSection = content.indexOf('\n##', insertPos + 1);
    const before = content.slice(0, insertPos);
    const after = nextSection !== -1 ? content.slice(nextSection) : '';
    const existing = content.slice(insertPos, nextSection !== -1 ? nextSection : undefined).trim();
    const activeLines = existing === 'None' || existing === '' ? '' : existing + '\n';
    content = before + '\n\n' + activeLines + `**${stage.name}:** In progress\n` + after;
  }

  syncAndWrite(statePath, content);
  output({ started: true, stage: stageId, stage_name: stage.name }, raw);
}

function cmdStateCompleteStage(cwd, stageId, outputPaths, raw) {
  const stage = getStage(stageId);
  if (!stage) error(`Unknown stage: ${stageId}`);

  const statePath = path.join(getOutputDir(cwd), 'STATE.md');
  let content = safeReadFile(statePath);
  if (!content) error('STATE.md not found');

  const date = new Date().toISOString().split('T')[0];

  // Mark checklist item complete
  const checkRegex = new RegExp(`- \\[ \\] ${stage.name}(?:\\s|$)`);
  content = content.replace(checkRegex, `- [x] ${stage.name} — done (${date})`);

  // Remove from Active Stages
  const activeRegex = new RegExp(`\\*\\*${stage.name}:\\*\\*.*\\n?`, 'g');
  content = content.replace(activeRegex, '');

  // Clean up empty Active Stages section
  content = content.replace(/(## Active Stages\n+)\s*\n(##)/g, '$1\nNone\n\n$2');

  // Add to Outputs table
  for (const op of outputPaths) {
    const row = `| ${stage.name} | ${path.basename(op)} | ${op} | ${date} |`;
    content = content.replace(/(## Outputs Produced\n\|.*\n\|.*\n)/, `$1${row}\n`);
  }

  // Check if all stages complete
  const allComplete = STAGE_SEQUENCE.every(id => {
    if (id === stageId) return true;
    const s = getStage(id);
    return content.includes(`- [x] ${s.name}`);
  });
  if (allComplete) {
    content = stateReplaceField(content, 'Status', 'Complete') || content;
  }

  syncAndWrite(statePath, content);
  output({ completed: true, stage: stageId, stage_name: stage.name }, raw);
}

function cmdStateRecordSession(cwd, stoppedAt, raw) {
  const statePath = path.join(getOutputDir(cwd), 'STATE.md');
  let content = safeReadFile(statePath);
  if (!content) error('STATE.md not found');

  const date = new Date().toISOString().split('T')[0];
  content = stateReplaceField(content, 'Last Session', date) || content;
  if (stoppedAt) {
    content = stateReplaceField(content, 'Stopped At', stoppedAt) || content;
  }

  syncAndWrite(statePath, content);
  output({ recorded: true }, raw);
}

// ─── Exports ─────────────────────────────────────────────────────────────────

module.exports = {
  extractFrontmatter,
  reconstructFrontmatter,
  stripFrontmatter,
  buildStateFrontmatter,
  syncAndWrite,
  stateReplaceField,
  cmdStateLoad,
  cmdStateJson,
  cmdStateStartStage,
  cmdStateCompleteStage,
  cmdStateRecordSession,
};
