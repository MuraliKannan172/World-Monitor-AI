# HANDOFF — Phase 0-9 Complete

## What's Done
- docs/ADR.md — full architecture decisions
- app/ — all Python modules (db, config, feeds, geo, data_pipeline, severity, ollama_client, rag, map_handler, websocket_manager, scheduler, main)
- static/ — index.html, style.css, app.js (glassmorphic UI)
- tests/ — test_pipeline.py, test_rag.py, test_api.py
- scripts/bootstrap.ps1 + bootstrap.sh
- CLAUDE.md, README.md, .env.example, .gitignore, .claudeignore, pyproject.toml, requirements.txt

## What's Next
- Install deps: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
- Run tests: `pytest tests/ -v`
- Start Ollama + pull model, then `python -m app.main`

## Known Gaps
- pydeck 3D view requires mapbox token for satellite tile style; falls back gracefully to no-tile style
- Folium WS script references `/ws` route — ensure frontend domain matches backend port
- cities1000.txt auto-downloaded on first startup (requires internet once)
