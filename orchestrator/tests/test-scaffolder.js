import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { initDb, closeDb, projectCreate, getDb } from '../src/db.js';
import { scaffoldProject } from '../src/scaffolder.js';

let tmpDir;
let projectsDir;

before(() => {
  tmpDir = mkdtempSync(join(tmpdir(), 'nsaf-scaffold-test-'));
  projectsDir = join(tmpDir, 'projects');
  initDb(join(tmpDir, 'test.db'));

  // Insert a test idea
  const db = getDb();
  db.prepare(`
    INSERT INTO ideas (id, date, source, rank, name, description, category, complexity, suggested_stack)
    VALUES (1, '2026-04-01', 'openai', 3, 'Fitness Tracker', 'Track workouts and progress', 'fitness', 'medium', '{"frontend":"React","backend":"Node.js","database":"PostgreSQL","css":"Tailwind"}')
  `).run();
});

after(() => {
  closeDb();
  rmSync(tmpDir, { recursive: true, force: true });
});

describe('Project scaffolder', () => {
  it('creates project directory with sdd-output', () => {
    const dir = join(projectsDir, 'fitness-tracker');
    const project = { slug: 'fitness-tracker', idea_id: 1, project_dir: dir };
    const ports = { portStart: 5020, portEnd: 5029 };
    const dbInfo = { dbName: 'nsaf_fitness_tracker', connectionString: 'postgresql://user:pass@localhost:5432/nsaf_fitness_tracker' };

    scaffoldProject(project, ports, dbInfo, { portStart: 5020, portEnd: 5029 });

    assert.ok(existsSync(join(dir, 'sdd-output')));
  });

  it('writes vision document with idea metadata', () => {
    const dir = join(projectsDir, 'fitness-tracker');
    const vision = readFileSync(join(dir, 'sdd-output', 'vision-document.md'), 'utf-8');
    assert.ok(vision.includes('Fitness Tracker'));
    assert.ok(vision.includes('Track workouts'));
    assert.ok(vision.includes('fitness'));
    assert.ok(vision.includes('React'));
  });

  it('writes .env with ports and database', () => {
    const dir = join(projectsDir, 'fitness-tracker');
    const env = readFileSync(join(dir, '.env'), 'utf-8');
    assert.ok(env.includes('PORT=5020'));
    assert.ok(env.includes('DATABASE_URL='));
    assert.ok(env.includes('nsaf_fitness_tracker'));
  });

  it('writes .gitignore', () => {
    const dir = join(projectsDir, 'fitness-tracker');
    const gitignore = readFileSync(join(dir, '.gitignore'), 'utf-8');
    assert.ok(gitignore.includes('node_modules'));
    assert.ok(gitignore.includes('.env'));
  });

  it('initializes git repo', () => {
    const dir = join(projectsDir, 'fitness-tracker');
    assert.ok(existsSync(join(dir, '.git')));
  });

  it('handles project without idea_id', () => {
    const dir = join(projectsDir, 'no-idea-app');
    const project = { slug: 'no-idea-app', idea_id: null, project_dir: dir };
    const ports = { portStart: 5030, portEnd: 5039 };

    scaffoldProject(project, ports, null, {});

    assert.ok(existsSync(join(dir, 'sdd-output', 'vision-document.md')));
    const vision = readFileSync(join(dir, 'sdd-output', 'vision-document.md'), 'utf-8');
    assert.ok(vision.includes('no-idea-app'));
  });
});
