import sqlite3
import os
import threading

_local = threading.local()
_db_path = None


def get_db(db_path=None):
    global _db_path
    if db_path is not None:
        _db_path = db_path

    # Check for existing connection on this thread
    db = getattr(_local, "db", None)
    if db is not None:
        return db

    path = _db_path or os.environ.get("NSAF_DB_PATH", "./nsaf.db")
    _db_path = path
    db = sqlite3.connect(path, timeout=5.0, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    _local.db = db
    return db


def close_db():
    db = getattr(_local, "db", None)
    if db is not None:
        db.close()
        _local.db = None


def reset_db(db_path=None):
    close_db()
    return get_db(db_path)


# --- Idea operations ---


def ideas_insert(idea):
    db = get_db()
    cursor = db.execute(
        """INSERT INTO ideas (date, source, rank, name, description, category, complexity, suggested_stack, temperature, tier)
           VALUES (:date, :source, :rank, :name, :description, :category, :complexity, :suggested_stack,
                   :temperature, :tier)""",
        {**{"temperature": 0, "tier": "unknown"}, **idea},
    )
    db.commit()
    return cursor.lastrowid


def ideas_insert_batch(ideas):
    db = get_db()
    padded = [{**{"temperature": 0, "tier": "unknown"}, **idea} for idea in ideas]
    db.executemany(
        """INSERT INTO ideas (date, source, rank, name, description, category, complexity, suggested_stack, temperature, tier)
           VALUES (:date, :source, :rank, :name, :description, :category, :complexity, :suggested_stack,
                   :temperature, :tier)""",
        padded,
    )
    db.commit()


def ideas_for_date(date):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM ideas WHERE date = ? ORDER BY source, rank", (date,)
    ).fetchall()
    return [dict(r) for r in rows]


def idea_get(id):
    db = get_db()
    row = db.execute("SELECT * FROM ideas WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None


# --- Idea history ---


def history_insert(name, description, date):
    db = get_db()
    db.execute(
        "INSERT INTO idea_history (name, description, date) VALUES (?, ?, ?)",
        (name, description, date),
    )
    db.commit()


def history_insert_batch(items):
    db = get_db()
    db.executemany(
        "INSERT INTO idea_history (name, description, date) VALUES (:name, :description, :date)",
        items,
    )
    db.commit()


def history_all():
    db = get_db()
    rows = db.execute("SELECT * FROM idea_history ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]


# --- Story idea operations ---


STORY_IDEAS_SCHEMA = """
CREATE TABLE IF NOT EXISTS story_ideas (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    rank INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    target_age TEXT,
    length_minutes INTEGER,
    art_style_hint TEXT,
    themes TEXT,
    temperature REAL,
    tier TEXT,
    selected INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS story_idea_history (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_story_ideas_date ON story_ideas(date);
"""


def story_ideas_init():
    db = get_db()
    db.executescript(STORY_IDEAS_SCHEMA)


def story_ideas_insert_batch(ideas):
    db = get_db()
    padded = [
        {
            "temperature": 0,
            "tier": "unknown",
            "target_age": None,
            "length_minutes": None,
            "art_style_hint": None,
            "themes": None,
            **idea,
        }
        for idea in ideas
    ]
    db.executemany(
        """INSERT INTO story_ideas (date, source, rank, name, description, target_age,
               length_minutes, art_style_hint, themes, temperature, tier)
           VALUES (:date, :source, :rank, :name, :description, :target_age,
                   :length_minutes, :art_style_hint, :themes, :temperature, :tier)""",
        padded,
    )
    db.commit()


def story_ideas_for_date(date):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM story_ideas WHERE date = ? ORDER BY source, rank", (date,)
    ).fetchall()
    return [dict(r) for r in rows]


def story_idea_get(id):
    db = get_db()
    row = db.execute("SELECT * FROM story_ideas WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None


def story_history_insert_batch(items):
    db = get_db()
    db.executemany(
        "INSERT INTO story_idea_history (name, description, date) VALUES (:name, :description, :date)",
        items,
    )
    db.commit()


def story_history_all():
    db = get_db()
    rows = db.execute("SELECT * FROM story_idea_history ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]


# --- Study idea operations ---


STUDY_IDEAS_SCHEMA = """
CREATE TABLE IF NOT EXISTS study_ideas (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    rank INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    level TEXT,
    chapters INTEGER,
    suggested_source_url TEXT,
    temperature REAL,
    tier TEXT,
    selected INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS study_idea_history (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_study_ideas_date ON study_ideas(date);
"""


def study_ideas_init():
    db = get_db()
    db.executescript(STUDY_IDEAS_SCHEMA)


def study_ideas_insert_batch(ideas):
    db = get_db()
    padded = [
        {
            "temperature": 0,
            "tier": "unknown",
            "level": None,
            "chapters": None,
            "suggested_source_url": None,
            **idea,
        }
        for idea in ideas
    ]
    db.executemany(
        """INSERT INTO study_ideas (date, source, rank, name, description, level,
               chapters, suggested_source_url, temperature, tier)
           VALUES (:date, :source, :rank, :name, :description, :level,
                   :chapters, :suggested_source_url, :temperature, :tier)""",
        padded,
    )
    db.commit()


def study_ideas_for_date(date):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM study_ideas WHERE date = ? ORDER BY source, rank", (date,)
    ).fetchall()
    return [dict(r) for r in rows]


def study_idea_get(id):
    db = get_db()
    row = db.execute("SELECT * FROM study_ideas WHERE id = ?", (id,)).fetchone()
    return dict(row) if row else None


def study_history_insert_batch(items):
    db = get_db()
    db.executemany(
        "INSERT INTO study_idea_history (name, description, date) VALUES (:name, :description, :date)",
        items,
    )
    db.commit()


def study_history_all():
    db = get_db()
    rows = db.execute("SELECT * FROM study_idea_history ORDER BY date DESC").fetchall()
    return [dict(r) for r in rows]


def ensure_project_idea_link_columns():
    """Add story_idea_id / study_idea_id columns to the projects table if missing."""
    db = get_db()
    cols = {r[1] for r in db.execute("PRAGMA table_info(projects)").fetchall()}
    if "story_idea_id" not in cols:
        db.execute("ALTER TABLE projects ADD COLUMN story_idea_id INTEGER")
    if "study_idea_id" not in cols:
        db.execute("ALTER TABLE projects ADD COLUMN study_idea_id INTEGER")
    db.commit()


# --- Vision session operations ---


VISION_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS vision_sessions (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    person_id TEXT,
    email TEXT,
    raw_idea TEXT NOT NULL,
    interpretation TEXT,
    proposed_kind TEXT,
    vision_md TEXT,
    status TEXT NOT NULL DEFAULT 'drafted',
    mode TEXT,
    project_slug TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_vision_sessions_slug ON vision_sessions(slug);
"""


def vision_init():
    db = get_db()
    db.executescript(VISION_SESSIONS_SCHEMA)


VISION_ALLOWED_FIELDS = frozenset({
    "person_id", "email", "raw_idea", "interpretation", "proposed_kind",
    "vision_md", "status", "mode", "project_slug",
})


def vision_insert(session):
    """Insert a new vision session. session must have at least slug + raw_idea."""
    vision_init()
    db = get_db()
    cols = ["slug", "raw_idea"] + [k for k in VISION_ALLOWED_FIELDS if k in session and k not in ("raw_idea",)]
    placeholders = ", ".join(f":{c}" for c in cols)
    col_list = ", ".join(cols)
    cursor = db.execute(
        f"INSERT INTO vision_sessions ({col_list}) VALUES ({placeholders})",
        session,
    )
    db.commit()
    return cursor.lastrowid


def vision_get(slug):
    vision_init()
    db = get_db()
    row = db.execute("SELECT * FROM vision_sessions WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


def vision_update(slug, **fields):
    if not fields:
        return
    invalid = set(fields.keys()) - VISION_ALLOWED_FIELDS
    if invalid:
        raise ValueError(f"Invalid vision_sessions fields: {invalid}")
    db = get_db()
    fields["updated_at"] = "datetime('now')"
    sets = ", ".join(f"{k} = ?" for k in fields if k != "updated_at")
    sets += ", updated_at = datetime('now')"
    values = [v for k, v in fields.items() if k != "updated_at"] + [slug]
    db.execute(f"UPDATE vision_sessions SET {sets} WHERE slug = ?", values)
    db.commit()


def vision_list(limit=20):
    vision_init()
    db = get_db()
    rows = db.execute(
        "SELECT * FROM vision_sessions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Project operations ---


def project_create(slug, idea_id, project_dir):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO projects (slug, idea_id, project_dir) VALUES (?, ?, ?)",
        (slug, idea_id, project_dir),
    )
    db.commit()
    return cursor.lastrowid


ALLOWED_PROJECT_FIELDS = frozenset({
    "status", "project_type", "port_start", "port_end", "db_name", "sdd_phase",
    "sdd_active_role", "sdd_progress", "deployed_url", "render_url",
    "last_state_change", "stall_alerted", "started_at", "completed_at",
})


def project_update(slug, **fields):
    if not fields:
        return
    invalid = set(fields.keys()) - ALLOWED_PROJECT_FIELDS
    if invalid:
        raise ValueError(f"Invalid field names: {invalid}")
    db = get_db()
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [slug]
    db.execute(f"UPDATE projects SET {sets} WHERE slug = ?", values)
    db.commit()


def project_get(slug):
    db = get_db()
    row = db.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


def projects_by_status(status):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM projects WHERE status = ?", (status,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Queue operations ---


def queue_enqueue(project_id):
    db = get_db()
    row = db.execute("SELECT COALESCE(MAX(position), 0) as max FROM queue").fetchone()
    db.execute(
        "INSERT INTO queue (project_id, position) VALUES (?, ?)",
        (project_id, row["max"] + 1),
    )
    db.commit()


def queue_remove(project_id):
    db = get_db()
    db.execute("DELETE FROM queue WHERE project_id = ?", (project_id,))
    db.commit()


def queue_list():
    db = get_db()
    rows = db.execute(
        """SELECT q.position, p.*
           FROM queue q JOIN projects p ON q.project_id = p.id
           ORDER BY q.position ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


# --- Config operations ---


def config_get(key):
    db = get_db()
    row = db.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def config_set(key, value):
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value))
    )
    db.commit()
