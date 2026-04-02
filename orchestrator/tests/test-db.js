import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import {
  initDb, getDb, closeDb,
  queueEnqueue, queueDequeue, queuePeek, queueRemove, queueList,
  projectCreate, projectUpdate, projectGet, projectGetById, projectsByStatus,
  portAllocate, portDeallocate, portGetForProject,
  configGet, configSet, configGetBool,
  ideasForDate, ideaGet
} from '../src/db.js';

let tmpDir;

before(() => {
  tmpDir = mkdtempSync(join(tmpdir(), 'nsaf-test-'));
  initDb(join(tmpDir, 'test.db'));
});

after(() => {
  closeDb();
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('Schema initialization', () => {
  it('creates all tables', () => {
    const db = getDb();
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
    const names = tables.map(t => t.name);
    assert.ok(names.includes('ideas'));
    assert.ok(names.includes('idea_history'));
    assert.ok(names.includes('projects'));
    assert.ok(names.includes('queue'));
    assert.ok(names.includes('ports'));
    assert.ok(names.includes('config'));
  });

  it('uses WAL mode', () => {
    const db = getDb();
    const mode = db.pragma('journal_mode', { simple: true });
    assert.equal(mode, 'wal');
  });
});

describe('Config operations', () => {
  it('get returns null for missing key', () => {
    assert.equal(configGet('nonexistent'), null);
  });

  it('set and get', () => {
    configSet('test_key', 'test_value');
    assert.equal(configGet('test_key'), 'test_value');
  });

  it('set overwrites existing', () => {
    configSet('test_key', 'new_value');
    assert.equal(configGet('test_key'), 'new_value');
  });

  it('getBool returns correct boolean', () => {
    configSet('flag_true', 'true');
    configSet('flag_false', 'false');
    configSet('flag_one', '1');
    assert.equal(configGetBool('flag_true'), true);
    assert.equal(configGetBool('flag_false'), false);
    assert.equal(configGetBool('flag_one'), true);
    assert.equal(configGetBool('missing_flag'), false);
  });
});

describe('Project operations', () => {
  let projectId;

  it('creates a project', () => {
    projectId = projectCreate({ slug: 'test-app', ideaId: null, projectDir: '/tmp/test-app' });
    assert.ok(projectId > 0);
  });

  it('gets project by slug', () => {
    const p = projectGet('test-app');
    assert.equal(p.slug, 'test-app');
    assert.equal(p.status, 'queued');
    assert.equal(p.project_dir, '/tmp/test-app');
  });

  it('gets project by id', () => {
    const p = projectGetById(projectId);
    assert.equal(p.slug, 'test-app');
  });

  it('returns null for missing project', () => {
    assert.equal(projectGet('nonexistent'), null);
  });

  it('updates project fields', () => {
    projectUpdate('test-app', { status: 'building', sdd_phase: 'design' });
    const p = projectGet('test-app');
    assert.equal(p.status, 'building');
    assert.equal(p.sdd_phase, 'design');
  });

  it('lists projects by status', () => {
    const building = projectsByStatus('building');
    assert.ok(building.length >= 1);
    assert.ok(building.every(p => p.status === 'building'));
  });
});

describe('Queue operations', () => {
  let pid1, pid2, pid3;

  before(() => {
    pid1 = projectCreate({ slug: 'q-app-1', ideaId: null, projectDir: '/tmp/q1' });
    pid2 = projectCreate({ slug: 'q-app-2', ideaId: null, projectDir: '/tmp/q2' });
    pid3 = projectCreate({ slug: 'q-app-3', ideaId: null, projectDir: '/tmp/q3' });
  });

  it('enqueues projects in order', () => {
    queueEnqueue(pid1);
    queueEnqueue(pid2);
    queueEnqueue(pid3);
    const list = queueList();
    assert.equal(list.length, 3);
    assert.equal(list[0].id, pid1);
    assert.equal(list[1].id, pid2);
    assert.equal(list[2].id, pid3);
  });

  it('peek returns first without removing', () => {
    const peeked = queuePeek();
    assert.equal(peeked.project_id, pid1);
    assert.equal(queueList().length, 3);
  });

  it('dequeue returns and removes first', () => {
    const item = queueDequeue();
    assert.equal(item.project_id, pid1);
    assert.equal(queueList().length, 2);
  });

  it('remove by project id', () => {
    queueRemove(pid2);
    const list = queueList();
    assert.equal(list.length, 1);
    assert.equal(list[0].id, pid3);
  });

  it('dequeue returns null when empty', () => {
    queueDequeue(); // remove pid3
    assert.equal(queueDequeue(), null);
  });
});

describe('Port operations', () => {
  let portProjectId;

  before(() => {
    portProjectId = projectCreate({ slug: 'port-app', ideaId: null, projectDir: '/tmp/port' });
  });

  it('allocates a port batch', () => {
    const ports = portAllocate(portProjectId, 5020, 5999, 10);
    assert.equal(ports.portStart, 5020);
    assert.equal(ports.portEnd, 5029);
  });

  it('get ports for project', () => {
    const ports = portGetForProject(portProjectId);
    assert.equal(ports.port_start, 5020);
    assert.equal(ports.port_end, 5029);
  });

  it('allocates next available batch', () => {
    const pid2 = projectCreate({ slug: 'port-app-2', ideaId: null, projectDir: '/tmp/port2' });
    const ports = portAllocate(pid2, 5020, 5999, 10);
    assert.equal(ports.portStart, 5030);
    assert.equal(ports.portEnd, 5039);
  });

  it('deallocates and reclaims', () => {
    portDeallocate(portProjectId);
    assert.equal(portGetForProject(portProjectId), null);
    const pid3 = projectCreate({ slug: 'port-app-3', ideaId: null, projectDir: '/tmp/port3' });
    const ports = portAllocate(pid3, 5020, 5999, 10);
    assert.equal(ports.portStart, 5020);
  });

  it('throws when range exhausted', () => {
    const pid = projectCreate({ slug: 'port-exhaust', ideaId: null, projectDir: '/tmp/pe' });
    assert.throws(() => portAllocate(pid, 5020, 5029, 10), /No available port batches/);
  });
});

describe('Idea operations', () => {
  it('reads ideas for date', () => {
    const db = getDb();
    db.prepare(`
      INSERT INTO ideas (date, source, rank, name, description, category, complexity, suggested_stack)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run('2026-04-01', 'openai', 1, 'Test App', 'A test app', 'productivity', 'medium', '{}');

    const ideas = ideasForDate('2026-04-01');
    assert.ok(ideas.length >= 1);
    assert.equal(ideas[0].name, 'Test App');
  });

  it('gets idea by id', () => {
    const ideas = ideasForDate('2026-04-01');
    const idea = ideaGet(ideas[0].id);
    assert.equal(idea.name, 'Test App');
  });

  it('returns null for missing idea', () => {
    assert.equal(ideaGet(99999), null);
  });
});
