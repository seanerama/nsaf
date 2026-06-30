'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ─── Project Root Resolution ─────────────────────────────────────────────────

function resolveProjectRoot(startDir) {
  let dir = startDir || process.cwd();
  while (dir !== path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, 'story-output'))) return dir;
    dir = path.dirname(dir);
  }
  return process.cwd();
}

function getOutputDir(projectRoot) {
  return path.join(projectRoot, 'story-output');
}

// ─── Output Helpers ───────────���──────────────────────────────────────────────

function output(result, raw, rawValue) {
  if (raw && rawValue !== undefined) {
    process.stdout.write(String(rawValue));
  } else {
    const json = JSON.stringify(result, null, 2);
    if (json.length > 50000) {
      const tmp = path.join(os.tmpdir(), `story-tools-${Date.now()}.json`);
      fs.writeFileSync(tmp, json);
      process.stdout.write(`@file:${tmp}`);
    } else {
      process.stdout.write(json);
    }
  }
}

function error(message) {
  console.error(`Error: ${message}`);
  process.exit(1);
}

// ─── File Utilities ────────���───────────────────────────────���─────────────────

function safeReadFile(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8');
  } catch {
    return null;
  }
}

function pathExists(targetPath) {
  return fs.existsSync(targetPath);
}

// ─── Slug Generation ��────────────────────────────────────────────────────────

function generateSlug(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40);
}

function currentTimestamp() {
  return new Date().toISOString();
}

// ─── Exports ────────────���────────────────────────────────────────────────────

module.exports = {
  resolveProjectRoot,
  getOutputDir,
  output,
  error,
  safeReadFile,
  pathExists,
  generateSlug,
  currentTimestamp,
};
