#!/usr/bin/env node
'use strict';

/**
 * story-tools — CLI dispatcher for Story Maker pipeline state management.
 *
 * Usage: node story-tools.cjs <command> <subcommand> [args...] [--raw] [--cwd <path>]
 *
 * Commands:
 *   state    load|json|start-stage|complete-stage|record-session
 *   graph    next|status|check
 *   config   ensure|get|set
 *   stage    list|info|outputs
 *   init     start|run-stage|status
 */

const path = require('path');
const fs = require('fs');
const { resolveProjectRoot, getOutputDir, output, error, safeReadFile, pathExists } = require('./lib/core.cjs');

// ─── Parse Global Flags ──────────────────────────────────────────────────────

const rawArgs = process.argv.slice(2);
let raw = false;
let cwd = process.cwd();
const cleanArgs = [];

for (let i = 0; i < rawArgs.length; i++) {
  if (rawArgs[i] === '--raw') { raw = true; continue; }
  if (rawArgs[i] === '--cwd' && rawArgs[i + 1]) { cwd = rawArgs[++i]; continue; }
  cleanArgs.push(rawArgs[i]);
}

const [command, subcommand, ...rest] = cleanArgs;

if (!command) {
  console.log('Usage: story-tools <command> <subcommand> [args...]');
  console.log('Commands: state, graph, config, stage, init');
  process.exit(0);
}

// ─── Parse --output and --stopped-at flags ───────────────────────────────────

function parseFlags(args) {
  const flags = { outputs: [], stoppedAt: null };
  const positional = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--output' && args[i + 1]) {
      flags.outputs.push(args[++i]);
    } else if (args[i] === '--stopped-at' && args[i + 1]) {
      flags.stoppedAt = args[++i];
    } else {
      positional.push(args[i]);
    }
  }
  return { positional, flags };
}

// ─── Command: state ──────────────────────────────────────────────────────────

if (command === 'state') {
  const state = require('./lib/state.cjs');

  switch (subcommand) {
    case 'load':
      state.cmdStateLoad(cwd, raw);
      break;
    case 'json':
      state.cmdStateJson(cwd, raw);
      break;
    case 'start-stage': {
      const stageId = rest[0];
      if (!stageId) error('Usage: state start-stage <stage-id>');
      state.cmdStateStartStage(cwd, stageId, raw);
      break;
    }
    case 'complete-stage': {
      const { positional, flags } = parseFlags(rest);
      const stageId = positional[0];
      if (!stageId) error('Usage: state complete-stage <stage-id> --output <path>');
      state.cmdStateCompleteStage(cwd, stageId, flags.outputs, raw);
      break;
    }
    case 'record-session': {
      const { flags } = parseFlags(rest);
      state.cmdStateRecordSession(cwd, flags.stoppedAt, raw);
      break;
    }
    default:
      error(`Unknown state subcommand: ${subcommand}\nAvailable: load, json, start-stage, complete-stage, record-session`);
  }
}

// ─── Command: graph ──────────────────────────────────────────────────────────

else if (command === 'graph') {
  const graph = require('./lib/graph.cjs');

  switch (subcommand) {
    case 'next':
      graph.cmdGraphNext(cwd, raw);
      break;
    case 'status':
      graph.cmdGraphStatus(cwd, raw);
      break;
    case 'check': {
      const stageId = rest[0];
      if (!stageId) error('Usage: graph check <stage-id>');
      graph.cmdGraphCheck(cwd, stageId, raw);
      break;
    }
    default:
      error(`Unknown graph subcommand: ${subcommand}\nAvailable: next, status, check`);
  }
}

// ─── Command: config ─────────────────────────────────────────────────────────

else if (command === 'config') {
  const config = require('./lib/config.cjs');

  switch (subcommand) {
    case 'ensure':
      config.cmdConfigEnsure(cwd, raw);
      break;
    case 'get':
      config.cmdConfigGet(cwd, rest[0], raw);
      break;
    case 'set':
      config.cmdConfigSet(cwd, rest[0], rest[1], raw);
      break;
    default:
      error(`Unknown config subcommand: ${subcommand}\nAvailable: ensure, get, set`);
  }
}

// ─── Command: stage ──────────────────────────────────────────────────────────

else if (command === 'stage') {
  const stages = require('./lib/stages.cjs');

  switch (subcommand) {
    case 'list':
      stages.cmdStageList(raw);
      break;
    case 'info': {
      const stageId = rest[0];
      if (!stageId) error('Usage: stage info <stage-id>');
      stages.cmdStageInfo(stageId, raw);
      break;
    }
    case 'outputs': {
      const stageId = rest[0];
      if (!stageId) error('Usage: stage outputs <stage-id>');
      stages.cmdStageOutputs(stageId, raw);
      break;
    }
    default:
      error(`Unknown stage subcommand: ${subcommand}\nAvailable: list, info, outputs`);
  }
}

// ─── Command: init ───────────────────────────────────────────────────────────

else if (command === 'init') {
  const config = require('./lib/config.cjs');
  const { getStage, STAGE_SEQUENCE } = require('./lib/stages.cjs');

  switch (subcommand) {
    case 'start': {
      const dir = getOutputDir(cwd);
      const stateExists = pathExists(path.join(dir, 'STATE.md'));
      let resumeInfo = null;
      if (stateExists) {
        const graph = require('./lib/graph.cjs');
        const state = graph.loadState(cwd);
        if (state) {
          const next = graph.getNextStages(state);
          resumeInfo = { status: state.status, completed: state.completed_stages, next };
        }
      }
      output({
        output_dir_exists: pathExists(dir),
        state_exists: stateExists,
        resume_info: resumeInfo,
        config: config.loadConfig(cwd),
        cwd,
      }, raw);
      break;
    }
    case 'run-stage': {
      const stageId = rest[0];
      if (!stageId) error('Usage: init run-stage <stage-id>');
      const stage = getStage(stageId);
      if (!stage) error(`Unknown stage: ${stageId}`);

      const graph = require('./lib/graph.cjs');
      const state = graph.loadState(cwd);

      let canRun = { can_run: true };
      let existingOutputs = {};

      if (state) {
        canRun = graph.canStageRun(stageId, state);

        // Gather outputs from completed stages
        for (const completedId of state.completed_stages) {
          const cs = getStage(completedId);
          if (cs) {
            const existing = cs.outputs.filter(o => {
              const full = path.join(cwd, o);
              return pathExists(full);
            });
            if (existing.length > 0) existingOutputs[completedId] = existing;
          }
        }
      }

      output({
        stage_id: stage.id,
        stage_name: stage.name,
        command: stage.command,
        phase: stage.phase,
        can_run: canRun.can_run,
        already_complete: canRun.already_complete || false,
        missing_deps: canRun.missing || null,
        reason: canRun.reason || null,
        expected_outputs: stage.outputs,
        existing_outputs: existingOutputs,
        config: config.loadConfig(cwd),
      }, raw);
      break;
    }
    case 'status': {
      const graph = require('./lib/graph.cjs');
      const state = graph.loadState(cwd);
      if (!state) error('STATE.md not found. Run /story:start first.');
      const status = graph.getGraphStatus(state);
      output(status, raw);
      break;
    }
    default:
      error(`Unknown init subcommand: ${subcommand}\nAvailable: start, run-stage, status`);
  }
}

// ─── Unknown Command ─────────────────────────────────────────────────────────

else {
  error(`Unknown command: ${command}\nAvailable: state, graph, config, stage, init`);
}
