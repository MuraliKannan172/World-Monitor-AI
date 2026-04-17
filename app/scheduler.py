"""APScheduler integration for periodic feed ingestion."""

import asyncio
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from spacy import Language

from app import data_pipeline
from app.config import settings
from app.websocket_manager import manager

_scheduler = AsyncIOScheduler()


async def _ingest_and_broadcast(nlp: Language, severity_queue: asyncio.Queue) -> None:
    await data_pipeline.run_ingest_cycle(nlp, severity_queue)
    await manager.broadcast({"type": "ingest_complete"})


def start(nlp: Language, severity_queue: asyncio.Queue) -> None:
    interval = settings.feed_interval_minutes * 60
    jitter = random.uniform(0, settings.feed_jitter_seconds)

    _scheduler.add_job(
        _ingest_and_broadcast,
        "interval",
        seconds=interval,
        jitter=jitter,
        args=[nlp, severity_queue],
        id="feed_ingest",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: ingest every {}m (jitter {}s)",
        settings.feed_interval_minutes,
        int(jitter),
    )


def stop() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
