# CLAUDE.md — WorldMonitor AI Project Memory

## What This Is
Local OSINT dashboard: 55+ RSS feeds → spaCy NER → SQLite → FastAPI + WebSocket → Folium/pydeck maps + Ollama RAG chatbot. Zero external API keys. Fully offline after first run.

## Key Conventions
- All async: FastAPI lifespan events, `asyncio.to_thread()` for spaCy, `aiosqlite` for DB.
- spaCy model (`en_core_web_sm`) loaded once in `app.state.nlp` at startup — never per-request.
- Severity scoring is background-only — never blocks ingest.
- WebSocket manager: `app/websocket_manager.py` → `ConnectionManager` class.
- BM25 RAG: FTS5 built-in, no external vector DB.
- Folium map rendered once; live markers injected via JS/Leaflet on WS `new_event`.

## Model Defaults
- Default Ollama model: `qwen2.5:7b`
- Context window: 8192 tokens

## Gotchas
- `cities1000.txt` downloaded from GeoNames on first run (7MB zip). Gated on file-exists check.
- SQLite WAL mode enabled in `db.py` `startup` event — not at schema creation time.
- `apscheduler` uses `AsyncIOScheduler`, not `BackgroundScheduler`.
- Alpine.js loaded from CDN; no build step for frontend.
- 3D pydeck view loaded lazily (iframe swap) to avoid deck.gl parsing on first paint.

## Phase Status
See `docs/HANDOFF_*.md` for per-phase completion notes.

## Running
```
python -m app.main          # Start server at http://localhost:8000
ollama serve                # Must be running for chatbot
ollama pull qwen2.5:7b      # Pull model once
python -m spacy download en_core_web_sm  # NLP model
```
This file guides Claude Code in this repository.

## Operating Principles

- Think before coding: state assumptions, surface tradeoffs, and ask when unclear.
- Keep it simple: implement only what is requested; avoid speculative abstractions.
- Make surgical changes: touch only what is necessary; do not refactor unrelated code.
- Stay goal-driven: define success criteria and verify them before finishing.
- Prefer readability over cleverness and match existing style.

## Token and Context Discipline

- Keep context usage below 80% capacity.
- Summarize large files instead of pasting them wholesale.
- Use agents for multi-file or high-complexity tasks.
- Prefer retrieval and targeted reads over full-project scans.
- Keep individual files under 800 lines when possible; for ML training files, aim for under 300 lines.
