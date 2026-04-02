import Database from 'better-sqlite3';
import { resolve } from 'path';

let db;

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    rank INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    complexity TEXT NOT NULL,
    suggested_stack TEXT,
    selected INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS idea_history (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    idea_id INTEGER REFERENCES ideas(id),
    slug TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    port_start INTEGER,
    port_end INTEGER,
    db_name TEXT,
    project_dir TEXT NOT NULL,
    sdd_phase TEXT,
    sdd_active_role TEXT,
    sdd_progress INTEGER DEFAULT 0,
    deployed_url TEXT,
    render_url TEXT,
    last_state_change TEXT,
    stall_alerted INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    position INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS ports (
    port_start INTEGER PRIMARY KEY,
    port_end INTEGER NOT NULL,
    project_id INTEGER REFERENCES projects(id),
    allocated_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_ideas_date ON ideas(date);
  CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
  CREATE INDEX IF NOT EXISTS idx_queue_position ON queue(position);
`;

export function initDb(dbPath) {
  db = new Database(resolve(dbPath));
  db.pragma('journal_mode = WAL');
  db.pragma('busy_timeout = 5000');
  db.exec(SCHEMA);
  return db;
}

export function getDb() {
  if (!db) throw new Error('Database not initialized. Call initDb() first.');
  return db;
}

export function closeDb() {
  if (db) {
    db.close();
    db = null;
  }
}

// --- Queue operations ---

export function queueEnqueue(projectId) {
  const maxPos = db.prepare('SELECT COALESCE(MAX(position), 0) as max FROM queue').get();
  db.prepare('INSERT INTO queue (project_id, position) VALUES (?, ?)').run(projectId, maxPos.max + 1);
}

export function queueDequeue() {
  const row = db.prepare(`
    SELECT q.id as queue_id, q.project_id, q.position, p.*
    FROM queue q JOIN projects p ON q.project_id = p.id
    ORDER BY q.position ASC LIMIT 1
  `).get();
  if (!row) return null;
  db.prepare('DELETE FROM queue WHERE id = ?').run(row.queue_id);
  return row;
}

export function queuePeek() {
  return db.prepare(`
    SELECT q.id as queue_id, q.project_id, q.position, p.*
    FROM queue q JOIN projects p ON q.project_id = p.id
    ORDER BY q.position ASC LIMIT 1
  `).get() || null;
}

export function queueRemove(projectId) {
  db.prepare('DELETE FROM queue WHERE project_id = ?').run(projectId);
}

export function queueList() {
  return db.prepare(`
    SELECT q.position, p.*
    FROM queue q JOIN projects p ON q.project_id = p.id
    ORDER BY q.position ASC
  `).all();
}

// --- Project operations ---

export function projectCreate({ slug, ideaId, projectDir }) {
  const result = db.prepare(`
    INSERT INTO projects (slug, idea_id, project_dir) VALUES (?, ?, ?)
  `).run(slug, ideaId, projectDir);
  return result.lastInsertRowid;
}

export function projectUpdate(slug, fields) {
  const keys = Object.keys(fields);
  if (keys.length === 0) return;
  const sets = keys.map(k => `${k} = @${k}`).join(', ');
  db.prepare(`UPDATE projects SET ${sets} WHERE slug = @slug`).run({ ...fields, slug });
}

export function projectGet(slug) {
  return db.prepare('SELECT * FROM projects WHERE slug = ?').get(slug) || null;
}

export function projectGetById(id) {
  return db.prepare('SELECT * FROM projects WHERE id = ?').get(id) || null;
}

export function projectsByStatus(status) {
  return db.prepare('SELECT * FROM projects WHERE status = ?').all(status);
}

export function projectsActiveToday() {
  const today = new Date().toISOString().slice(0, 10);
  return db.prepare(`
    SELECT * FROM projects
    WHERE date(created_at) = ? OR date(started_at) = ? OR date(completed_at) = ?
  `).all(today, today, today);
}

// --- Port operations ---

export function portAllocate(projectId, rangeStart = 5020, rangeEnd = 5999, batchSize = 10) {
  const allocated = db.prepare('SELECT port_start, port_end FROM ports ORDER BY port_start').all();

  for (let start = rangeStart; start + batchSize - 1 <= rangeEnd; start += batchSize) {
    const end = start + batchSize - 1;
    const conflict = allocated.some(a => !(end < a.port_start || start > a.port_end));
    if (!conflict) {
      db.prepare('INSERT INTO ports (port_start, port_end, project_id) VALUES (?, ?, ?)').run(start, end, projectId);
      return { portStart: start, portEnd: end };
    }
  }
  throw new Error('No available port batches in range');
}

export function portDeallocate(projectId) {
  db.prepare('DELETE FROM ports WHERE project_id = ?').run(projectId);
}

export function portGetForProject(projectId) {
  return db.prepare('SELECT * FROM ports WHERE project_id = ?').get(projectId) || null;
}

// --- Config operations ---

export function configGet(key) {
  const row = db.prepare('SELECT value FROM config WHERE key = ?').get(key);
  return row ? row.value : null;
}

export function configSet(key, value) {
  db.prepare('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)').run(key, String(value));
}

export function configGetBool(key) {
  const val = configGet(key);
  return val === 'true' || val === '1';
}

// --- Idea operations (read-only from Node side) ---

export function ideasForDate(date) {
  return db.prepare('SELECT * FROM ideas WHERE date = ? ORDER BY source, rank').all(date);
}

export function ideaGet(id) {
  return db.prepare('SELECT * FROM ideas WHERE id = ?').get(id) || null;
}
