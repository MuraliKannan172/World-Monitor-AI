"""Async RSS ingestion with spaCy NER and offline geocoding."""

import asyncio
import hashlib
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp
import feedparser
from loguru import logger
from spacy import Language

from app import db, geo
from app.feeds import FEEDS, FeedSource


def _compute_sha256(title: str, link: str) -> str:
    return hashlib.sha256(f"{title}{link}".encode()).hexdigest()


def _parse_date(entry: Any) -> datetime | None:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).astimezone(timezone.utc)
            except Exception:
                pass
    return None


async def _fetch_feed_text(url: str, session: aiohttp.ClientSession) -> str | None:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception as exc:
        logger.debug("Feed fetch error {}: {}", url, exc)
    return None


def _extract_locations(nlp: Language, text: str) -> list[geo.GeoMatch]:
    doc = nlp(text)
    matches = []
    seen = set()
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            key = ent.text.lower()
            if key not in seen:
                seen.add(key)
                match = geo.resolve(ent.text)
                if match:
                    matches.append(match)
    return matches


async def _process_entry(
    entry: Any,
    source: FeedSource,
    nlp: Language,
    severity_queue: asyncio.Queue,
) -> None:
    title = getattr(entry, "title", "").strip()
    link = getattr(entry, "link", "").strip()
    if not title or not link:
        return

    sha256 = _compute_sha256(title, link)
    summary = getattr(entry, "summary", "") or ""
    published_at = _parse_date(entry)

    # Run spaCy NER in a thread (CPU-bound)
    text_for_ner = f"{title} {summary}"[:1000]
    locations: list[geo.GeoMatch] = await asyncio.to_thread(
        _extract_locations, nlp, text_for_ner
    )
    first_loc = locations[0] if locations else None

    article = {
        "sha256": sha256,
        "title": title,
        "summary": summary[:500] if summary else None,
        "link": link,
        "source_name": source.name,
        "category": source.category,
        "published_at": published_at.isoformat() if published_at else None,
        "lat": first_loc.lat if first_loc else None,
        "lon": first_loc.lon if first_loc else None,
        "country": first_loc.country if first_loc else None,
        "city": first_loc.city if first_loc else None,
    }

    new_id = await db.insert_article(article)
    if new_id:
        logger.debug("Inserted article id={} from {}", new_id, source.name)
        try:
            severity_queue.put_nowait((new_id, title))
        except asyncio.QueueFull:
            pass  # Severity scoring non-critical; drop if queue full


async def ingest_feed(
    source: FeedSource,
    nlp: Language,
    session: aiohttp.ClientSession,
    severity_queue: asyncio.Queue,
) -> int:
    """Fetch and process one feed. Returns count of new articles."""
    raw = await _fetch_feed_text(source.url, session)
    if not raw:
        return 0

    parsed = await asyncio.to_thread(feedparser.parse, raw)
    tasks = [
        _process_entry(entry, source, nlp, severity_queue)
        for entry in parsed.entries
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    return len(parsed.entries)


async def run_ingest_cycle(nlp: Language, severity_queue: asyncio.Queue) -> None:
    """Ingest all feeds with per-feed jitter."""
    logger.info("Starting ingest cycle for {} feeds", len(FEEDS))
    async with aiohttp.ClientSession(
        headers={"User-Agent": "WorldMonitorAI/1.0 RSS Reader"}
    ) as session:
        for source in FEEDS:
            jitter = random.uniform(0, 2)  # small in-cycle jitter
            await asyncio.sleep(jitter)
            await ingest_feed(source, nlp, session, severity_queue)
    logger.info("Ingest cycle complete")
