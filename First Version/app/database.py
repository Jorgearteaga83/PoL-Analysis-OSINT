from __future__ import annotations  # Import necessary module or component

import sqlite3  # Import necessary module or component
from typing import Iterable, List  # Import necessary module or component

from app.config import DB_PATH  # Import necessary module or component
from app.scraper import Post  # Import necessary module or component


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


def get_connection() -> sqlite3.Connection:  # Define function get_connection
    conn = sqlite3.connect(DB_PATH)  # Assign value to conn
    conn.row_factory = sqlite3.Row  # Assign value to conn.row_factory
    return conn  # Return value from function


def initialise_database() -> None:  # Define function initialise_database
    conn = get_connection()  # Assign value to conn
    try:  # Start of try block for exception handling
        conn.executescript(SCHEMA_SQL)  # Close bracket/parenthesis
        conn.commit()  # Close bracket/parenthesis
    finally:  # Execute cleanup code regardless of exceptions
        conn.close()  # Close bracket/parenthesis


def save_posts(posts: Iterable[Post]) -> None:  # Define function save_posts
    conn = get_connection()  # Assign value to conn
    try:  # Start of try block for exception handling
        cur = conn.cursor()  # Assign value to cur
        for p in posts:  # Iterate in a loop
            cur.execute(  # Execute statement or expression
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
                (  # Execute statement or expression
                    p.post_id,  # Execute statement or expression
                    p.username,  # Execute statement or expression
                    p.text,  # Execute statement or expression
                    p.timestamp.isoformat(),  # Execute statement or expression
                    ";".join(p.image_urls),  # Execute statement or expression
                    ";".join(p.image_filenames),  # Execute statement or expression
                ),  # Close structure
            )  # Close bracket/parenthesis
        conn.commit()  # Close bracket/parenthesis
    finally:  # Execute cleanup code regardless of exceptions
        conn.close()  # Close bracket/parenthesis


def load_posts_from_db(username: str) -> List[Post]:  # Define function load_posts_from_db
    conn = get_connection()  # Assign value to conn
    try:  # Start of try block for exception handling
        cur = conn.cursor()  # Assign value to cur
        cur.execute(  # Execute statement or expression
            "SELECT * FROM posts WHERE username = ? ORDER BY timestamp ASC",  # Execute statement or expression
            (username,),  # Execute statement or expression
        )  # Close bracket/parenthesis
        rows = cur.fetchall()  # Assign value to rows
    finally:  # Execute cleanup code regardless of exceptions
        conn.close()  # Close bracket/parenthesis
    from datetime import datetime  # Import necessary module or component
    posts: List[Post] = []  # Close bracket/parenthesis
    for r in rows:  # Iterate in a loop
        posts.append(  # Execute statement or expression
            Post(  # Call function Post
                post_id=r["id"],  # Assign value to post_id
                username=r["username"],  # Assign value to username
                text=r["text"] or "",  # Assign value to text
                timestamp=datetime.fromisoformat(r["timestamp"]),  # Assign value to timestamp
                image_urls=[u for u in (r["image_urls"] or "").split(";") if u],  # Assign value to image_urls
                image_filenames=[  # Assign value to image_filenames
                    f for f in (r["image_filenames"] or "").split(";") if f  # Execute statement or expression
                ],  # Close structure
            )  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
    return posts  # Return value from function
