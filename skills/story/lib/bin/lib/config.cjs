'use strict';

const fs = require('fs');
const path = require('path');
const { getOutputDir, safeReadFile, output, error } = require('./core.cjs');

// ─── Defaults ────────────────────────────────────────────────────────────────

const DEFAULTS = {
  art_style: 'watercolor storybook',
  resolution: '1920x1080',
  tts_provider: 'openai',
  tts_model: 'tts-1-hd',
  leonardo_model: 'auto',
  scene_transition: 'crossfade',
  transition_duration: 0.5,
  title_card_duration: 4,
  credits_duration: 3,
  output_format: 'mp4',
};

// ─── Merge ───────────────────────────────────────────────────────────────────

function deepMerge(left, right) {
  const result = { ...left };
  for (const [key, val] of Object.entries(right)) {
    if (val && typeof val === 'object' && !Array.isArray(val) && typeof result[key] === 'object') {
      result[key] = deepMerge(result[key], val);
    } else {
      result[key] = val;
    }
  }
  return result;
}

// ─── Load ────────────────────────────────────────────────────────────────────

function loadConfig(cwd) {
  const configPath = path.join(getOutputDir(cwd), 'config.json');
  const raw = safeReadFile(configPath);
  if (!raw) return { ...DEFAULTS };
  try {
    const project = JSON.parse(raw);
    return deepMerge(DEFAULTS, project);
  } catch {
    return { ...DEFAULTS };
  }
}

// ─── Dot-notation access ─────────────────────────────────────────────────────

function configGet(config, keyPath) {
  return keyPath.split('.').reduce((obj, key) => (obj && obj[key] !== undefined ? obj[key] : undefined), config);
}

function configSet(obj, keyPath, value) {
  const keys = keyPath.split('.');
  let target = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!target[keys[i]] || typeof target[keys[i]] !== 'object') target[keys[i]] = {};
    target = target[keys[i]];
  }
  target[keys[keys.length - 1]] = value;
  return obj;
}

// ─── CLI Commands ────────────────────────────────────────────────────────────

function cmdConfigEnsure(cwd, raw) {
  const dir = getOutputDir(cwd);
  const configPath = path.join(dir, 'config.json');
  if (fs.existsSync(configPath)) {
    output({ created: false, path: 'story-output/config.json' }, raw);
    return;
  }
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(configPath, JSON.stringify(DEFAULTS, null, 2));
  output({ created: true, path: 'story-output/config.json' }, raw);
}

function cmdConfigGet(cwd, keyPath, raw) {
  const config = loadConfig(cwd);
  if (keyPath) {
    const val = configGet(config, keyPath);
    output({ key: keyPath, value: val }, raw, val);
  } else {
    output(config, raw);
  }
}

function cmdConfigSet(cwd, keyPath, value, raw) {
  if (!keyPath || value === undefined) error('Usage: config set <key> <value>');
  const dir = getOutputDir(cwd);
  const configPath = path.join(dir, 'config.json');
  const rawContent = safeReadFile(configPath);
  let project = {};
  if (rawContent) {
    try { project = JSON.parse(rawContent); } catch { /* ignore */ }
  }
  // Coerce value
  let coerced = value;
  if (value === 'true') coerced = true;
  else if (value === 'false') coerced = false;
  else if (/^\d+(\.\d+)?$/.test(value)) coerced = parseFloat(value);

  configSet(project, keyPath, coerced);
  fs.writeFileSync(configPath, JSON.stringify(project, null, 2));
  output({ set: true, key: keyPath, value: coerced }, raw);
}

// ─── Exports ─────────────────────────────────────────────────────────────────

module.exports = {
  DEFAULTS,
  loadConfig,
  deepMerge,
  configGet,
  configSet,
  cmdConfigEnsure,
  cmdConfigGet,
  cmdConfigSet,
};
