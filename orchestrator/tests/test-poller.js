import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { initDb, closeDb, projectCreate, projectUpdate, projectGet } from '../src/db.js';
import { parseStateMd, pollProject } from '../src/poller.js';
import { checkStalls } from '../src/stall.js';

let tmpDir;

before(() => {
  tmpDir = mkdtempSync(join(tmpdir(), 'nsaf-poller-test-'));
  initDb(join(tmpDir, 'test.db'));
});

after(() => {
  closeDb();
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('STATE.md parser', () => {
  it('parses frontmatter fields', () => {
    const content = `---
sdd_state_version: "1.0"
workflow_path: "new"
current_phase: "implementation"
status: "in progress"
progress:
  total_roles: 11
  completed_roles: 5
  percent: 45
---

# SDD State

## Active Roles

**Stage Manager:** In progress
`;
    const state = parseStateMd(content);
    assert.equal(state.phase, 'implementation');
    assert.equal(state.status, 'in progress');
    assert.equal(state.progress, 45);
    assert.equal(state.activeRole, 'Stage Manager');
  });

  it('calculates progress from checklist when frontmatter missing', () => {
    const content = `---
sdd_state_version: "1.0"
current_phase: "testing"
status: "in progress"
progress:
  percent: 0
---

## Completed Roles

- [x] Vision Assistant
- [x] Lead Architect
- [x] Project Planner
- [ ] Stage Manager
- [ ] Project Tester

## Active Roles

**Stage Manager:** In progress
`;
    const state = parseStateMd(content);
    assert.equal(state.progress, 60); // 3/5
    assert.equal(state.activeRole, 'Stage Manager');
  });

  it('detects complete status', () => {
    const content = `---
current_phase: "complete"
status: "complete"
progress:
  percent: 100
---

## Active Roles

None
`;
    const state = parseStateMd(content);
    assert.equal(state.status, 'complete');
    assert.equal(state.progress, 100);
  });

  it('handles malformed content', () => {
    const state = parseStateMd('just some random text');
    assert.ok(state);
    assert.equal(state.progress, 0);
  });
});

describe('Project polling', () => {
  it('updates project state from STATE.md', () => {
    const projectDir = join(tmpDir, 'poll-test-1');
    mkdirSync(join(projectDir, 'sdd-output'), { recursive: true });
    writeFileSync(join(projectDir, 'sdd-output', 'STATE.md'), `---
current_phase: "design"
status: "in progress"
progress:
  percent: 20
---

## Active Roles

**Lead Architect:** In progress
`);

    const pid = projectCreate({ slug: 'poll-test-1', ideaId: null, projectDir });
    projectUpdate('poll-test-1', { status: 'building' });

    const result = pollProject(projectGet('poll-test-1'));

    const updated = projectGet('poll-test-1');
    assert.equal(updated.sdd_phase, 'design');
    assert.equal(updated.sdd_active_role, 'Lead Architect');
    assert.equal(updated.sdd_progress, 20);
  });

  it('detects completion', () => {
    const projectDir = join(tmpDir, 'poll-complete');
    mkdirSync(join(projectDir, 'sdd-output'), { recursive: true });
    writeFileSync(join(projectDir, 'sdd-output', 'STATE.md'), `---
current_phase: "complete"
status: "complete"
progress:
  percent: 100
---
`);

    projectCreate({ slug: 'poll-complete', ideaId: null, projectDir });
    projectUpdate('poll-complete', { status: 'building' });

    const result = pollProject(projectGet('poll-complete'));
    assert.equal(result.complete, true);
  });
});

describe('Stall detection', () => {
  it('detects stalled project', () => {
    projectCreate({ slug: 'stall-test', ideaId: null, projectDir: '/tmp/stall' });
    // Set last_state_change to 60 minutes ago
    const past = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    projectUpdate('stall-test', {
      status: 'building',
      last_state_change: past,
      started_at: past,
    });

    const stalled = checkStalls(30); // 30 min timeout
    assert.ok(stalled.length >= 1);
    assert.ok(stalled.some(p => p.slug === 'stall-test'));

    // Verify stall_alerted was set
    const p = projectGet('stall-test');
    assert.equal(p.stall_alerted, 1);
  });

  it('does not re-alert already alerted project', () => {
    // stall-test already has stall_alerted = 1
    const stalled = checkStalls(30);
    assert.ok(!stalled.some(p => p.slug === 'stall-test'));
  });

  it('does not flag recent projects', () => {
    projectCreate({ slug: 'fresh-build', ideaId: null, projectDir: '/tmp/fresh' });
    projectUpdate('fresh-build', {
      status: 'building',
      last_state_change: new Date().toISOString(),
    });

    const stalled = checkStalls(30);
    assert.ok(!stalled.some(p => p.slug === 'fresh-build'));
  });
});
