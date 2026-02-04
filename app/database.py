from __future__ import annotations

import sqlite3
from typing import Iterable, List

from app.config import DB_PATH
from app.scraper import Post


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    text TEXT,
    timestamp TEXT NOT NULL,
    image_urls TEXT,
    image_filenames TEXT
);

CREATE TABLE IF NOT EXISTS sentiment (
    post_id TEXT PRIMARY KEY,
    compound REAL,
    pos REAL,
    neu REAL,
    neg REAL,
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ocr_results (
    post_id TEXT PRIMARY KEY,
    image_filename TEXT,
    raw_text TEXT,
    notes TEXT,
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialise_database() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def save_posts(posts: Iterable[Post]) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        for p in posts:
            cur.execute(
                """
                INSERT INTO posts (id, username, text, timestamp, image_urls, image_filenames)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    text = excluded.text,
                    timestamp = excluded.timestamp,
                    image_urls = excluded.image_urls,
                    image_filenames = excluded.image_filenames
                """,
                (
                    p.post_id,
                    p.username,
                    p.text,
                    p.timestamp.isoformat(),
                    ";".join(p.image_urls),
                    ";".join(p.image_filenames),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def load_posts_from_db(username: str) -> List[Post]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM posts WHERE username = ? ORDER BY timestamp ASC",
            (username,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    from datetime import datetime
    posts: List[Post] = []
    for r in rows:
        posts.append(
            Post(
                post_id=r["id"],
                username=r["username"],
                text=r["text"] or "",
                timestamp=datetime.fromisoformat(r["timestamp"]),
                image_urls=[u for u in (r["image_urls"] or "").split(";") if u],
                image_filenames=[
                    f for f in (r["image_filenames"] or "").split(";") if f
                ],
            )
        )
    return posts
