"""Async Ollama client wrapper."""

from typing import AsyncIterator

import ollama as _ollama
from loguru import logger

from app.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self._client = _ollama.AsyncClient(host=settings.ollama_base_url)

    async def list_models(self) -> list[str]:
        try:
            resp = await self._client.list()
            return [m.model for m in resp.models]
        except Exception as exc:
            logger.warning("Ollama unreachable: {}", exc)
            return []

    async def generate(self, prompt: str, model: str | None = None) -> dict:
        """Non-streaming generate for severity scoring."""
        m = model or settings.ollama_default_model
        try:
            resp = await self._client.generate(
                model=m,
                prompt=prompt,
                options={"num_ctx": settings.ollama_num_ctx},
            )
            return {"response": resp.response}
        except Exception as exc:
            logger.warning("Ollama generate error: {}", exc)
            return {"response": ""}

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield token strings from Ollama streaming chat."""
        m = model or settings.ollama_default_model
        try:
            stream = await self._client.chat(
                model=m,
                messages=messages,
                stream=True,
                options={
                    "num_ctx": settings.ollama_num_ctx,
                    "num_predict": 1024,
                    "temperature": 0.7,
                },
                keep_alive="10m",
            )
            async for chunk in stream:
                token = chunk.message.content
                if token:
                    yield token
        except Exception as exc:
            logger.warning("Ollama stream error: {}", exc)
            yield f"[Error: {exc}]"


# Singleton — instantiated at app startup
ollama = OllamaClient()
