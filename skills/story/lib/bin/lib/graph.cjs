'use strict';

const { getOutputDir, safeReadFile, output, error } = require('./core.cjs');
const { STAGES, PHASES, STAGE_SEQUENCE, getStage, getAllStages } = require('./stages.cjs');
const { extractFrontmatter } = require('./state.cjs');
const path = require('path');

// ─── State Helpers ───────────────────────────────────────────────────────────

function loadState(cwd) {
  const statePath = path.join(getOutputDir(cwd), 'STATE.md');
  const content = safeReadFile(statePath);
  if (!content) return null;
  const fm = extractFrontmatter(content);
  return {
    completed_stages: fm.completed_stages || [],
    active_stages: fm.active_stages || [],
    status: fm.status || 'not_started',
  };
}

function isStageComplete(stageId, state) {
  return state.completed_stages.includes(stageId);
}

function isStageActive(stageId, state) {
  return state.active_stages.includes(stageId);
}

// ─── Dependency Resolution ───────────────────────────────────────────────────

function canStageRun(stageId, state) {
  const stage = getStage(stageId);
  if (!stage) return { can_run: false, reason: `Unknown stage: ${stageId}` };

  if (isStageComplete(stageId, state)) {
    return { can_run: true, already_complete: true };
  }

  const missing = [];
  for (const depId of stage.depends_on) {
    if (!isStageComplete(depId, state)) {
      missing.push(depId);
    }
  }

  if (missing.length > 0) {
    return {
      can_run: false,
      reason: `Missing dependencies: ${missing.join(', ')}`,
      missing,
    };
  }

  return { can_run: true };
}

// ──�� Next Stages ─────────────────────────────────────────────────────────────

function getNextStages(state) {
  const available = [];

  for (const stageId of STAGE_SEQUENCE) {
    if (isStageComplete(stageId, state)) continue;
    if (isStageActive(stageId, state)) continue;

    const check = canStageRun(stageId, state);
    if (!check.can_run) continue;
    if (check.already_complete) continue;

    const stage = getStage(stageId);
    const parallelWith = stage.parallel_with
      .filter(pid => {
        if (isStageComplete(pid, state)) return false;
        if (isStageActive(pid, state)) return false;
        const pcheck = canStageRun(pid, state);
        return pcheck.can_run && !pcheck.already_complete;
      })
      .map(pid => {
        const ps = getStage(pid);
        return { stage_id: ps.id, name: ps.name, command: ps.command };
      });

    available.push({
      stage_id: stage.id,
      name: stage.name,
      command: stage.command,
      phase: stage.phase,
      phase_name: PHASES[stage.phase]?.name || stage.phase,
      description: stage.description,
      parallel_with: parallelWith,
    });
  }

  return available;
}

// ──��� Graph Status ────────────────────────────────────────────────────────────

function getGraphStatus(state) {
  const completed = state.completed_stages.map(id => {
    const s = getStage(id);
    return s ? { stage_id: s.id, name: s.name, command: s.command } : { stage_id: id };
  });

  const active = state.active_stages.map(id => {
    const s = getStage(id);
    return s ? { stage_id: s.id, name: s.name, command: s.command } : { stage_id: id };
  });

  const available = getNextStages(state);

  const waiting = [];
  for (const stageId of STAGE_SEQUENCE) {
    if (isStageComplete(stageId, state)) continue;
    if (isStageActive(stageId, state)) continue;
    const check = canStageRun(stageId, state);
    if (check.can_run) continue;
    const s = getStage(stageId);
    waiting.push({
      stage_id: s.id,
      name: s.name,
      reason: check.reason,
      missing: check.missing,
    });
  }

  return {
    progress: {
      completed: state.completed_stages.length,
      total: STAGE_SEQUENCE.length,
      percent: Math.round((state.completed_stages.length / STAGE_SEQUENCE.length) * 100),
    },
    completed,
    active,
    available,
    waiting,
  };
}

// ─── CLI Commands ────────────────────────────────────────────────────────────

function cmdGraphNext(cwd, raw) {
  const state = loadState(cwd);
  if (!state) error('STATE.md not found. Run /story:start first.');
  const next = getNextStages(state);
  output(next, raw);
}

function cmdGraphStatus(cwd, raw) {
  const state = loadState(cwd);
  if (!state) error('STATE.md not found. Run /story:start first.');
  const status = getGraphStatus(state);
  output(status, raw);
}

function cmdGraphCheck(cwd, stageId, raw) {
  const state = loadState(cwd);
  if (!state) error('STATE.md not found. Run /story:start first.');
  const result = canStageRun(stageId, state);
  output(result, raw);
}

// ─── Exports ─────────────────────────────────────────────────────────────────

module.exports = {
  loadState,
  isStageComplete,
  isStageActive,
  canStageRun,
  getNextStages,
  getGraphStatus,
  cmdGraphNext,
  cmdGraphStatus,
  cmdGraphCheck,
};
