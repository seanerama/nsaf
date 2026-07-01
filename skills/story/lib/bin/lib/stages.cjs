'use strict';

// ─── Stage Definitions ───────────────────────────────────────────────────────

const STAGES = {
  start: {
    id: 'start',
    name: 'Start',
    command: '/story:start',
    phase: 'setup',
    description: 'Capture story idea and initialize project',
    outputs: ['story-output/concept.md'],
    depends_on: [],
    parallel_with: [],
  },
  outline: {
    id: 'outline',
    name: 'Outline',
    command: '/story:outline',
    phase: 'writing',
    description: 'Build story arc, characters, scenes, and voice assignments',
    outputs: ['story-output/outline.md'],
    depends_on: ['start'],
    parallel_with: [],
  },
  write: {
    id: 'write',
    name: 'Write',
    command: '/story:write',
    phase: 'writing',
    description: 'Write full narration script with voice tags and illustration prompts',
    outputs: ['story-output/script.md'],
    depends_on: ['outline'],
    parallel_with: ['portraits'],
  },
  portraits: {
    id: 'portraits',
    name: 'Portraits',
    command: '/story:portraits',
    phase: 'production',
    description: 'Generate per-character hero portraits used as references by illustrate',
    outputs: ['story-output/characters/'],
    depends_on: ['outline'],
    parallel_with: ['write'],
  },
  illustrate: {
    id: 'illustrate',
    name: 'Illustrate',
    command: '/story:illustrate',
    phase: 'production',
    description: 'Generate scene illustrations via Nano Banana (with character portraits) or Leonardo',
    outputs: ['story-output/images/'],
    depends_on: ['write', 'portraits'],
    parallel_with: ['narrate'],
  },
  narrate: {
    id: 'narrate',
    name: 'Narrate',
    command: '/story:narrate',
    phase: 'production',
    description: 'Generate multi-voice audio narration via TTS',
    outputs: ['story-output/audio/'],
    depends_on: ['write'],
    parallel_with: ['illustrate'],
  },
  build: {
    id: 'build',
    name: 'Build',
    command: '/story:build',
    phase: 'assembly',
    description: 'Assemble images and audio into final MP4 video',
    outputs: ['story-output/final.mp4'],
    depends_on: ['illustrate', 'narrate'],
    parallel_with: ['pdf'],
  },
  pdf: {
    id: 'pdf',
    name: 'PDF',
    command: '/story:pdf',
    phase: 'assembly',
    description: 'Assemble a print-ready PDF picture book (8.5×8.5 square)',
    outputs: ['story-output/print-book.html'],
    depends_on: ['write', 'illustrate'],
    parallel_with: ['narrate', 'build'],
  },
};

const PHASES = {
  setup:      { order: 1, name: 'Setup',      description: 'Project initialization' },
  writing:    { order: 2, name: 'Writing',     description: 'Story content creation' },
  production: { order: 3, name: 'Production',  description: 'Media generation' },
  assembly:   { order: 4, name: 'Assembly',    description: 'Final video assembly' },
};

// ─── Stage sequence (ideal order) ────────────────────────────────────────────

const STAGE_SEQUENCE = ['start', 'outline', 'write', 'portraits', 'illustrate', 'narrate', 'build', 'pdf'];

// ─── Lookup Helpers ──────────────────────────────────────────────────────────

function getStage(stageId) {
  return STAGES[stageId] || null;
}

function getStageByCommand(command) {
  const cmd = command.replace(/^\/story:/, '');
  return STAGES[cmd] || null;
}

function getAllStages() {
  return STAGE_SEQUENCE.map(id => STAGES[id]);
}

function getStageOutputPaths(stageId) {
  const stage = getStage(stageId);
  return stage ? stage.outputs : [];
}

// ─── CLI Commands ────────────────────────────────────────────────────────────

function cmdStageList(raw) {
  const { output } = require('./core.cjs');
  const stages = getAllStages().map(s => ({
    id: s.id,
    name: s.name,
    command: s.command,
    phase: s.phase,
    description: s.description,
  }));
  output(stages, raw);
}

function cmdStageInfo(stageId, raw) {
  const { output, error } = require('./core.cjs');
  const stage = getStage(stageId);
  if (!stage) error(`Unknown stage: ${stageId}`);
  output(stage, raw);
}

function cmdStageOutputs(stageId, raw) {
  const { output, error } = require('./core.cjs');
  const stage = getStage(stageId);
  if (!stage) error(`Unknown stage: ${stageId}`);
  output(stage.outputs, raw);
}

// ─── Exports ─────────────────────────────────────────────────────────────────

module.exports = {
  STAGES,
  PHASES,
  STAGE_SEQUENCE,
  getStage,
  getStageByCommand,
  getAllStages,
  getStageOutputPaths,
  cmdStageList,
  cmdStageInfo,
  cmdStageOutputs,
};
