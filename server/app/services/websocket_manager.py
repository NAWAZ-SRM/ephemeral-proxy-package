import asyncio
from collections import defaultdict
from fastapi import WebSocket
import json


class WebSocketManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, slug: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.connections[slug].add(ws)

    async def disconnect(self, slug: str, ws: WebSocket):
        async with self._lock:
            self.connections[slug].discard(ws)

    async def broadcast(self, slug: str, message: dict):
        if slug not in self.connections:
            return
        
        dead = set()
        async with self._lock:
            conns = list(self.connections.get(slug, set()))
        
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        
        if dead:
            async with self._lock:
                self.connections[slug] -= dead

    def get_connection_count(self, slug: str) -> int:
        return len(self.connections.get(slug, set()))


ws_manager = WebSocketManager()
