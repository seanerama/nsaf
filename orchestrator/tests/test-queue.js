import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { initDb, closeDb, projectCreate, queueEnqueue, configSet } from '../src/db.js';
import { canDequeue, dequeueNext, getQueueDepth, getActiveCount, isPaused } from '../src/queue.js';

let tmpDir;

before(() => {
  tmpDir = mkdtempSync(join(tmpdir(), 'nsaf-queue-test-'));
  initDb(join(tmpDir, 'test.db'));
});

after(() => {
  closeDb();
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('Queue manager', () => {
  it('canDequeue returns true when slots available', () => {
    assert.equal(canDequeue(2), true);
  });

  it('canDequeue returns false when paused', () => {
    configSet('paused', 'true');
    assert.equal(canDequeue(2), false);
    configSet('paused', 'false');
  });

  it('isPaused reflects config', () => {
    assert.equal(isPaused(), false);
    configSet('paused', 'true');
    assert.equal(isPaused(), true);
    configSet('paused', 'false');
  });

  it('getQueueDepth returns correct count', () => {
    const pid1 = projectCreate({ slug: 'q-depth-1', ideaId: null, projectDir: '/tmp/qd1' });
    const pid2 = projectCreate({ slug: 'q-depth-2', ideaId: null, projectDir: '/tmp/qd2' });
    queueEnqueue(pid1);
    queueEnqueue(pid2);
    assert.equal(getQueueDepth(), 2);
  });

  it('dequeueNext returns and removes first item', () => {
    const item = dequeueNext();
    assert.ok(item);
    assert.equal(item.slug, 'q-depth-1');
    assert.equal(getQueueDepth(), 1);
  });

  it('getActiveCount returns 0 initially', () => {
    assert.equal(getActiveCount(), 0);
  });
});
