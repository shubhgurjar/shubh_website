import sqlite3
import json
from pathlib import Path
from typing import Optional, Any
from config import DB_PATH, SEED_PATH, DEFAULT_MASTER_PASSWORD
from auth import hash_password


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        # Domains table (e.g. AI/ML, System Design, Backend, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                icon TEXT DEFAULT 'folder',
                color TEXT DEFAULT 'indigo',
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Topics table (nested under domains or parent topics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain_id INTEGER NOT NULL,
                parent_id INTEGER,
                title TEXT NOT NULL,
                slug TEXT NOT NULL,
                summary TEXT,
                status TEXT DEFAULT 'in_progress', -- 'not_started', 'in_progress', 'mastered', 'reference'
                importance TEXT DEFAULT 'high',    -- 'core', 'high', 'medium', 'low'
                drive_folder_url TEXT,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE CASCADE
            );
        """)

        # Resources table (YouTube, Drive folders, Drive files, PDFs, Markdown notes, GitHub repos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                type TEXT NOT NULL, -- 'youtube', 'drive_folder', 'drive_file', 'pdf', 'note', 'article', 'github'
                title TEXT NOT NULL,
                url TEXT,
                file_path TEXT,
                notes TEXT,
                tags TEXT, -- JSON array of tags or comma separated
                is_favorite INTEGER DEFAULT 0,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            );
        """)

        # Indexes for fast search and joins
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topics_domain ON topics(domain_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topics_parent ON topics(parent_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_topic ON resources(topic_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);")

        conn.commit()

    # Set default password if not already set
    if get_setting("password_hash") is None:
        set_setting("password_hash", hash_password(DEFAULT_MASTER_PASSWORD))
        set_setting("auth_enabled", "true")
        set_setting("site_title", "Shubh's Software Engineering Knowledge Hub")


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def seed_default_data_if_empty():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM domains")
        count = cursor.fetchone()["count"]
        if count > 0:
            return  # Already seeded or has user data

        if not SEED_PATH.exists():
            return

        with open(SEED_PATH, "r", encoding="utf-8") as f:
            seed_data = json.load(f)

        domains = seed_data.get("domains", [])
        for d_idx, d in enumerate(domains):
            cursor.execute(
                """
                INSERT INTO domains (name, slug, description, icon, color, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    d.get("name"),
                    d.get("slug"),
                    d.get("description", ""),
                    d.get("icon", "folder"),
                    d.get("color", "indigo"),
                    d.get("order_index", d_idx),
                ),
            )
            domain_id = cursor.lastrowid

            topics = d.get("topics", [])
            for t_idx, t in enumerate(topics):
                cursor.execute(
                    """
                    INSERT INTO topics (domain_id, title, slug, summary, status, importance, drive_folder_url, order_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        domain_id,
                        t.get("title"),
                        t.get("slug"),
                        t.get("summary", ""),
                        t.get("status", "in_progress"),
                        t.get("importance", "high"),
                        t.get("drive_folder_url", ""),
                        t.get("order_index", t_idx),
                    ),
                )
                topic_id = cursor.lastrowid

                resources = t.get("resources", [])
                for r_idx, r in enumerate(resources):
                    tags = json.dumps(r.get("tags", [])) if isinstance(r.get("tags"), list) else (r.get("tags") or "[]")
                    cursor.execute(
                        """
                        INSERT INTO resources (topic_id, type, title, url, file_path, notes, tags, is_favorite, order_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            topic_id,
                            r.get("type", "note"),
                            r.get("title"),
                            r.get("url", ""),
                            r.get("file_path", ""),
                            r.get("notes", ""),
                            tags,
                            1 if r.get("is_favorite") else 0,
                            r.get("order_index", r_idx),
                        ),
                    )

        conn.commit()
