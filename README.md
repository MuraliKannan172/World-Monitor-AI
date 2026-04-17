# WorldMonitor AI

A production-grade, 100% local, open-source OSINT dashboard with integrated Ollama-powered RAG chatbot and glassmorphic UI.

**Zero external API keys. Runs fully offline after initial setup.**

## Features

- 55+ curated RSS feeds (world, geopolitics, conflict, cyber, energy, finance, regional)
- Automatic geo-extraction via spaCy NER + offline GeoNames gazetteer
- Interactive 2D Folium map (marker clusters + heatmap) with live WebSocket updates
- 3D pydeck globe visualization
- AI chatbot: BM25 RAG over SQLite FTS5 + local Ollama LLM (streaming)
- Runtime model switching (switch Ollama models mid-conversation)
- Filters: category, country, severity, date range
- Severity scoring (1-10) via background Ollama calls

## Quick Start (Windows)

```powershell
git clone <repo>
cd worldmonitor-ai
.\scripts\bootstrap.ps1

# In a separate terminal:
ollama serve
ollama pull qwen2.5:7b

python -m app.main
```

Open [http://localhost:8000](http://localhost:8000)

## Quick Start (Linux / macOS)

```bash
git clone <repo>
cd worldmonitor-ai
chmod +x scripts/bootstrap.sh && ./scripts/bootstrap.sh
ollama serve && ollama pull qwen2.5:7b
python -m app.main
```

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) installed locally (for chatbot; app works without it)
- 4GB+ RAM, 8GB+ GPU VRAM recommended

## Architecture

See `docs/ADR.md` for all architecture decisions.

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn + asyncio |
| Database | SQLite (WAL, FTS5 BM25) |
| NLP | spaCy en_core_web_sm |
| Geo | GeoNames cities1000 gazetteer + rapidfuzz |
| AI | Ollama (any local model) |
| Maps | Folium (2D) + pydeck (3D) |
| Frontend | Vanilla JS + Alpine.js + Tailwind CDN |

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
OLLAMA_DEFAULT_MODEL=qwen2.5:7b
FEED_INTERVAL_MINUTES=7
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Chatbot unavailable | Run `ollama serve` and `ollama pull qwen2.5:7b` |
| No events on map | Wait 60s for first ingest cycle; check `LOG_LEVEL=DEBUG` |
| Gazetteer download fails | Download `cities1000.zip` from geonames.org and extract to `data/` |
| Port in use | Set `PORT=8001` in `.env` |

## Running Tests

```bash
pytest tests/ -v
```
