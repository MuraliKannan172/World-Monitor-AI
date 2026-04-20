"""FastAPI application entrypoint."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import spacy
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app import db, geo, layers, scheduler, severity
from app.config import settings
from app.map_handler import render_2d, render_3d
from app.ollama_client import ollama
from app.rag import answer_stream
from app.websocket_manager import manager

_STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    logger.info("Starting WorldMonitor AI")
    await db.init_db()
    await geo.ensure_gazetteer()
    await asyncio.to_thread(geo.build_index)

    nlp = await asyncio.to_thread(spacy.load, "en_core_web_sm")
    app.state.nlp = nlp

    sev_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    app.state.severity_queue = sev_queue

    sev_task = asyncio.create_task(severity.severity_worker(sev_queue, ollama))
    app.state.severity_task = sev_task

    scheduler.start(nlp, sev_queue)

    # Run first ingest immediately in the background
    asyncio.create_task(
        data_pipeline_first_run(nlp, sev_queue)
    )

    yield

    # --- shutdown ---
    scheduler.stop()
    sev_task.cancel()
    try:
        await sev_task
    except asyncio.CancelledError:
        pass
    logger.info("WorldMonitor AI shutdown complete")


async def data_pipeline_first_run(nlp, sev_queue):
    from app import data_pipeline
    await data_pipeline.run_ingest_cycle(nlp, sev_queue)
    await manager.broadcast({"type": "ingest_complete"})


app = FastAPI(title="WorldMonitor AI", lifespan=lifespan)

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── HTML pages ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/map/2d", response_class=HTMLResponse)
async def map_2d():
    return HTMLResponse(await render_2d())


@app.get("/map/3d", response_class=HTMLResponse)
async def map_3d():
    return HTMLResponse(await render_3d())


# ── API endpoints ───────────────────────────────────────────────────────────

@app.get("/api/events")
async def get_events(
    categories: list[str] = Query(default=[]),
    countries: list[str] = Query(default=[]),
    min_severity: int = Query(default=0, ge=0, le=10),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    events = await db.fetch_events(
        categories=categories or None,
        countries=countries or None,
        min_severity=min_severity,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {"events": events, "count": len(events)}


@app.get("/api/models")
async def get_models():
    models = await ollama.list_models()
    return {"models": models, "default": settings.ollama_default_model}


@app.get("/api/layers")
async def get_layers():
    return layers.LAYER_DEFS


@app.get("/api/layers/{layer_id}")
async def get_layer_data(layer_id: str):
    from fastapi.responses import JSONResponse
    data = await layers.fetch_layer(layer_id)
    return JSONResponse(content=data)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── WebSocket ───────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive; client pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.websocket("/ws/chat")
async def chat_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_json()
            if payload.get("type") == "ping":
                continue
            question = payload.get("question", "").strip()
            model = payload.get("model") or None
            # Client provides session_id so history persists across messages
            session_id = payload.get("session_id") or str(uuid.uuid4())
            if not question:
                continue
            async for token in answer_stream(question, model, session_id):
                await ws.send_json({"type": "token", "content": token})
            await ws.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
