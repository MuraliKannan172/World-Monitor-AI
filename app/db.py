import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite
from loguru import logger

from app.config import settings

_DB_PATH = settings.db_path

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256       TEXT    UNIQUE NOT NULL,
    title        TEXT    NOT NULL,
    summary      TEXT,
    link         TEXT    NOT NULL,
    source_name  TEXT,
    category     TEXT,
    published_at DATETIME,
    ingested_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    lat          REAL,
    lon          REAL,
    country      TEXT,
    city         TEXT,
    severity     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_articles_latlon      ON articles(lat, lon);
CREATE INDEX IF NOT EXISTS idx_articles_cat_sev     ON articles(category, severity);
CREATE INDEX IF NOT EXISTS idx_articles_published   ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_country     ON articles(country);

CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title,
    summary,
    content="articles",
    content_rowid="id",
    tokenize="porter ascii"
);

CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary)
    VALUES (new.id, new.title, COALESCE(new.summary, ""));
END;

CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary)
    VALUES ("delete", old.id, old.title, COALESCE(old.summary, ""));
END;

CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary)
    VALUES ("delete", old.id, old.title, COALESCE(old.summary, ""));
    INSERT INTO articles_fts(rowid, title, summary)
    VALUES (new.id, new.title, COALESCE(new.summary, ""));
END;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    role       TEXT    CHECK(role IN ("user", "assistant")) NOT NULL,
    content    TEXT    NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_sessions(session_id, created_at);
"""


async def init_db() -> None:
    os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("Database initialized at {}", _DB_PATH)


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def insert_article(article: dict) -> int | None:
    """Insert article; return new row id or None if duplicate."""
    sql = """
        INSERT OR IGNORE INTO articles
            (sha256, title, summary, link, source_name, category, published_at, lat, lon, country, city)
        VALUES
            (:sha256, :title, :summary, :link, :source_name, :category, :published_at, :lat, :lon, :country, :city)
    """
    async with get_db() as db:
        cursor = await db.execute(sql, article)
        await db.commit()
        if cursor.lastrowid and cursor.rowcount:
            return cursor.lastrowid
    return None


async def update_severity(article_id: int, score: int) -> None:
    async with get_db() as db:
        await db.execute("UPDATE articles SET severity=? WHERE id=?", (score, article_id))
        await db.commit()


async def fetch_events(
    categories: list[str] | None = None,
    countries: list[str] | None = None,
    min_severity: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    conditions = ["1=1"]
    params: list = []

    if categories:
        placeholders = ",".join("?" * len(categories))
        conditions.append(f"category IN ({placeholders})")
        params.extend(categories)
    if countries:
        placeholders = ",".join("?" * len(countries))
        conditions.append(f"country IN ({placeholders})")
        params.extend(countries)
    if min_severity:
        conditions.append("severity >= ?")
        params.append(min_severity)
    if date_from:
        conditions.append("published_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("published_at <= ?")
        params.append(date_to)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT id, title, summary, link, source_name, category,
               published_at, ingested_at, lat, lon, country, city, severity
        FROM articles
        WHERE {where}
        ORDER BY published_at DESC
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]

    async with get_db() as db:
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def fts_search(query: str, limit: int = 8) -> list[dict]:
    """BM25 full-text search over articles for RAG context."""
    sql = """
        SELECT a.id, a.title, a.summary, a.link, a.source_name, a.published_at, a.country
        FROM articles_fts f
        JOIN articles a ON a.id = f.rowid
        WHERE articles_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    async with get_db() as db:
        cursor = await db.execute(sql, (query, limit))
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def save_chat_turn(session_id: str, role: str, content: str) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_sessions(session_id, role, content) VALUES(?,?,?)",
            (session_id, role, content),
        )
        await db.commit()
