"""WebSocket connection manager with simple fanout broadcast."""

import asyncio

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)
        logger.debug("WS connected; total={}", len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active = [c for c in self._active if c is not ws]
        logger.debug("WS disconnected; total={}", len(self._active))

    async def broadcast(self, data: dict) -> None:
        if not self._active:
            return
        dead = []
        results = await asyncio.gather(
            *[c.send_json(data) for c in self._active],
            return_exceptions=True,
        )
        for ws, result in zip(self._active, results):
            if isinstance(result, Exception):
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
