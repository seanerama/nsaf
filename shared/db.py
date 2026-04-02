import sqlite3
import os

_db = None


def get_db(db_path=None):
    global _db
    if _db is not None:
        return _db
    if db_path is None:
        db_path = os.environ.get("NSAF_DB_PATH", "./nsaf.db")
    _db = sqlite3.connect(db_path, timeout=5.0)
    _db.row_factory = sqlite3.Row
    _db.execute("PRAGMA journal_mode=WAL")
    _db.execute("PRAGMA busy_timeout=5000")
    return _db


def close_db():
    global _db
    if _db is not None:
        _db.close()
        _db = None


def reset_db(db_path=None):
    close_db()
    return get_db(db_path)


# --- Idea operations ---


def ideas_insert(idea):
    db = get_db()
    cursor = db.execute(
        """INSERT INTO ideas (date, source, rank, name, description, category, complexity, suggested_stack)
           VALUES (:date, :source, :rank, :name, :description, :category, :complexity, :suggested_stack)""",
        idea,
    )
    db.commit()
    return cursor.lastrowid


def ideas_insert_batch(ideas):
    db = get_db()
    db.executemany(
        """INSERT INTO ideas (date, source, rank, name, description, category, complexity, suggested_stack)
           VALUES (:date, :source, :rank, :name, :description, :category, :complexity, :suggested_stack)""",
        ideas,
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
    "status", "port_start", "port_end", "db_name", "sdd_phase",
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
