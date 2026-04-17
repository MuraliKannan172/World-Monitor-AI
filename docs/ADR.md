# Architecture Decision Record — WorldMonitor AI

**Date:** 2026-04-17  
**Status:** Accepted  
**Context:** Production-grade local OSINT dashboard; zero external API keys; RTX 5060 8GB / Windows 11 / Python 3.13.

---

## 1. Concurrency Model — spaCy NER

**Decision:** `asyncio.to_thread()` wraps each spaCy `.pipe()` call. spaCy model loaded once at startup via FastAPI `lifespan` event, stored in `app.state.nlp`.

**Rationale:** spaCy is CPU-bound and releases the GIL during C-level tokenization. `to_thread()` avoids blocking the asyncio event loop without the overhead of a full `ProcessPoolExecutor`. A thread pool (default size = `os.cpu_count()`) provides adequate throughput for 55 feeds ingested every 7 minutes.

**Rejected alternatives:** `ProcessPoolExecutor` — model pickling overhead; synchronous in-loop calls — blocks WebSocket broadcasts.

---

## 2. Database Schema and Indexing

**Decision:** SQLite with WAL mode, `synchronous=NORMAL`, and FTS5 virtual table for full-text search.

**Schema:**

```
articles (
  id          INTEGER PRIMARY KEY,
  sha256      TEXT UNIQUE NOT NULL,       -- dedup key: SHA-256(title+link)
  title       TEXT NOT NULL,
  summary     TEXT,
  link        TEXT NOT NULL,
  source_name TEXT,
  category    TEXT,
  published_at DATETIME,
  ingested_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  lat         REAL,
  lon         REAL,
  country     TEXT,
  city        TEXT,
  severity    INTEGER DEFAULT 0          -- 0 = unscored, 1-10 = scored
)

articles_fts (                           -- FTS5 virtual table
  content="articles",
  content_rowid="id",
  tokenize="porter ascii"
)

chat_sessions (
  id         INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL,
  role       TEXT CHECK(role IN ('user','assistant')),
  content    TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:** `(lat, lon)` composite for map bbox queries; `(category, severity)` for filter sidebar; `(published_at DESC)` for event feed sort.

**FTS5 BM25:** SQLite FTS5's built-in BM25 ranking is used for RAG retrieval. `rank_bm25` package omitted — FTS5's implementation is sufficient and avoids a pure-Python dependency.

---

## 3. RAG Retrieval Strategy

**Decision:** SQLite FTS5 BM25 (built-in) over article `title + summary` fields. Top 8 snippets injected into Ollama system prompt.

**Rationale:** Lightest possible implementation — no embedding model, no vector DB, no network calls. BM25 keyword search is appropriate for news-style OSINT content (high term specificity). For the corpus sizes expected (tens of thousands of articles), FTS5 BM25 returns sub-millisecond results.

**Rejected alternatives:**
- `sentence-transformers` (all-MiniLM-L6-v2): adds ~90MB model + GPU memory pressure. Optional future enhancement.
- `rank_bm25`: pure-Python BM25 outside SQLite — slower and redundant given FTS5.
- ChromaDB / Qdrant: heavyweight; contradicts zero-cloud-dependency principle.

---

## 4. WebSocket Broadcast Pattern

**Decision:** Single `ConnectionManager` holding a list of active `WebSocket` connections. Broadcast via `asyncio.gather(*[ws.send_json(data) for ws in self.active])`. Per-client `asyncio.Queue(maxsize=100)` added if broadcast lag becomes observable under load.

**Rationale:** For a personal dashboard with 1–5 concurrent clients, a simple list + gather is sufficient and debuggable. The `maxsize=100` queue guard (drop oldest on overflow) is architected as an upgrade path, not a day-one requirement.

---

## 5. Frontend State Management

**Decision:** Vanilla JS + Alpine.js v3 (loaded via CDN). No React, no build step.

**Rationale:** The dashboard is a single-page app with three interactive regions (filters, map, chat). Alpine.js provides reactive data binding (`x-data`, `x-on`, `x-bind`) without a bundler. Tailwind CSS via CDN handles utility styling. Chart.js for any severity histograms.

**3D lazy-load:** `pydeck`-rendered HTML (`/map/3d`) loaded into an iframe only when user clicks the 3D toggle — avoids loading deck.gl (~1.5MB) on initial page paint.

**Map live updates:** Folium renders the shell HTML once (server-side, on `/map/2d`). New markers injected client-side via Leaflet JS API calls triggered by WebSocket `new_event` messages — no server-side HTML regeneration per event.

---

## 6. Geo Resolution

**Decision:** Offline GeoNames `cities1000.txt` gazetteer. Downloaded once at first startup into `data/cities1000.txt` (gated on file existence check). spaCy GPE/LOC entities fuzzy-matched via `rapidfuzz` against city + country names in the gazetteer.

**Nominatim removed:** Online geocoding contradicts the zero-external-API constraint. All resolution is offline after the one-time gazetteer download (~7MB zip).

---

## 7. Severity Scoring

**Decision:** Async background queue. On article insert, article ID pushed to `asyncio.Queue`. A background worker (`severity.py`) pops IDs, calls Ollama with a compact prompt (`Rate severity 1-10 for: {title}`), updates the DB row. Ingest is never blocked.

**Graceful degradation:** If Ollama is down, severity stays 0 (unscored). Map and feed remain functional; markers render with a neutral color.

---

## 8. Ollama Integration

**Assumed runtime:** Ollama must be running locally (`ollama serve`) with at least one model pulled. This is a user-managed service, not a build-time dependency.

**Default context:** `OLLAMA_NUM_CTX=8192` (8 RAG snippets × ~400 tokens each = ~3200 tokens; 8192 leaves comfortable headroom for response on 8GB VRAM).

**Fallback:** If `ollama.list()` raises `ConnectionError`, frontend shows inline banner. App continues ingesting feeds normally.

---

## 9. Feed Scheduling

**Decision:** APScheduler `AsyncIOScheduler` with `IntervalTrigger` (7-minute base interval). Each feed assigned a random jitter offset (0–60s) on startup to avoid thundering herd on external servers.

---

## 10. Session Durability

Each phase commits to git with a conventional commit message. `docs/HANDOFF_<phase>.md` (≤20 lines) written at phase completion for session resumption.
