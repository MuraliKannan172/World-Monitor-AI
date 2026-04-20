"""RAG: BM25 retrieval via SQLite FTS5 + Google News RSS web search + Ollama."""

import asyncio
import re
from urllib.parse import quote

import aiohttp
import feedparser
from loguru import logger

from app import db
from app.ollama_client import ollama

_SYSTEM_PROMPT = (
    "You are WorldMonitor AI, an OSINT intelligence analyst and general assistant. "
    "You have access to a live feed of world events from 55+ news sources, "
    "and real-time web search results from Google News. "
    "Answer the user's question clearly and concisely. "
    "Cite sources with [1], [2] notation when context is provided. "
    "For general questions use your knowledge and any web context provided. "
    "Be direct, factual, and analytical."
)


def _parse_news_rss(feed_text: str, max_results: int = 5) -> list[dict]:
    feed = feedparser.parse(feed_text)
    results = []
    for entry in feed.entries[:max_results]:
        summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:400]
        results.append({
            "title": entry.get("title", ""),
            "body": summary,
            "url": entry.get("link", ""),
        })
    return results


async def _web_search(query: str) -> list[dict]:
    """Google News RSS search — free, no API key, real current news."""
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"Web search HTTP {resp.status}")
                    return []
                text = await resp.text()
        return await asyncio.to_thread(_parse_news_rss, text)
    except Exception as exc:
        logger.debug(f"Web search failed: {type(exc).__name__}: {exc}")
        return []


async def build_context(query: str, limit: int = 10) -> tuple[str, list[dict]]:
    """Combine local event RAG + web search into a context block (parallel fetch)."""
    snippets, web_results = await asyncio.gather(
        db.fts_search(query, limit=limit),
        _web_search(query),
    )

    lines = []
    for i, s in enumerate(snippets, start=1):
        date_str = (s.get("published_at") or "")[:10]
        lines.append(
            f"[{i}] {s['title']} ({s.get('source_name', '')} {date_str})\n"
            f"    {(s.get('summary') or '')[:300]}"
        )

    if web_results:
        lines.append("\n[Web Search Results]")
        for i, w in enumerate(web_results, start=len(snippets) + 1):
            lines.append(f"[{i}] {w['title']}\n    {w['body']}")

    return "\n\n".join(lines), snippets


async def answer_stream(question: str, model: str | None, session_id: str):
    """Retrieve context + history, build prompt, stream Ollama response, save turn."""
    context_block, _sources = await build_context(question)
    history = await db.get_chat_history(session_id, limit=20)

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if context_block:
        messages.append({"role": "system", "content": f"Retrieved context:\n{context_block}"})

    # Include up to last 10 turns of conversation history for multi-turn memory
    for turn in history[-10:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": question})

    await db.save_chat_turn(session_id, "user", question)

    full_response: list[str] = []
    async for token in ollama.stream_chat(messages, model=model):
        full_response.append(token)
        yield token

    await db.save_chat_turn(session_id, "assistant", "".join(full_response))
