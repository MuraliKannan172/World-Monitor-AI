"""Background severity scoring via Ollama."""

import asyncio
import re

from loguru import logger

from app import db


_PROMPT_TEMPLATE = (
    "Rate the global security/geopolitical severity of this news headline on a scale "
    "of 1 (trivial) to 10 (catastrophic). Reply with ONLY the integer.\n\nHeadline: {title}"
)


async def severity_worker(queue: asyncio.Queue, ollama_client) -> None:
    """Drain severity queue; run forever until cancelled."""
    while True:
        try:
            article_id, title = await queue.get()
            await _score_and_save(article_id, title, ollama_client)
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.debug("Severity worker error: {}", exc)


async def _score_and_save(article_id: int, title: str, ollama_client) -> None:
    try:
        prompt = _PROMPT_TEMPLATE.format(title=title[:200])
        response = await ollama_client.generate(prompt)
        text = response.get("response", "").strip()
        match = re.search(r"\b([1-9]|10)\b", text)
        if match:
            score = int(match.group(1))
            await db.update_severity(article_id, score)
            logger.debug("Scored article id={} severity={}", article_id, score)
    except Exception as exc:
        logger.debug("Severity score failed for id={}: {}", article_id, exc)
