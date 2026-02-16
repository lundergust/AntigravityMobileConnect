"""
WebSocket connection manager for the Antigravity Mobile Connect bridge.

Manages connected mobile clients and broadcasts agent responses.
"""

import asyncio
import json
from typing import Any, Dict, List, Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting.

    Maintains a set of active WebSocket connections and provides methods
    for broadcasting messages to all connected clients.
    """

    def __init__(self) -> None:
        """Initialize the connection manager with an empty connection set."""
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active set.

        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def send_personal(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send a JSON message to a specific client.

        Args:
            message: The message payload to send.
            websocket: The target WebSocket connection.
        """
        await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a JSON message to all connected clients.

        Args:
            message: The message payload to broadcast.
        """
        async with self._lock:
            disconnected: List[WebSocket] = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.active_connections.remove(conn)

    @property
    def client_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


# Global singleton
ws_manager = ConnectionManager()
