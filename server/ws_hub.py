"""
WebSocket connection manager for the Antigravity Mobile Connect bridge.

Manages connected mobile clients and broadcasts agent responses.
Phase 1: Added streaming broadcast helpers.
"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting.

    Maintains a set of active WebSocket connections and provides methods
    for broadcasting messages to all connected clients, including
    streaming token delivery.
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
        
        # Send initial snapshot immediately if available
        # Avoid import loop by importing inside method
        try:
            from server.bridge import cdp_bridge
            if cdp_bridge.last_messages:
                await websocket.send_json({
                    "type": "snapshot_update",
                    "messages": [
                        {
                            "id": msg.get("id", f"cdp-{i}"),
                            "role": msg.get("role", "assistant"),
                            "content": msg.get("content", ""),
                            "type": msg.get("type", "text"),
                        }
                        for i, msg in enumerate(cdp_bridge.last_messages)
                    ],
                    "count": len(cdp_bridge.last_messages),
                })
        except Exception as e:
            print(f"⚠️ Failed to send initial snapshot: {e}")

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
        try:
            await websocket.send_json(message)
        except Exception:
            pass

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

    async def broadcast_stream_start(self, message_id: str) -> None:
        """Broadcast a stream start event to all clients.

        Args:
            message_id: Unique identifier for the streaming message.
        """
        await self.broadcast({
            "type": "stream_start",
            "message_id": message_id,
        })

    async def broadcast_stream_chunk(self, message_id: str, chunk: str) -> None:
        """Broadcast a streaming text chunk to all clients.

        Args:
            message_id: The message being streamed.
            chunk: The text chunk to append.
        """
        await self.broadcast({
            "type": "stream_chunk",
            "message_id": message_id,
            "chunk": chunk,
        })

    async def broadcast_stream_end(self, message_id: str, content: str) -> None:
        """Broadcast a stream end event with the full content.

        Args:
            message_id: The message that finished streaming.
            content: The complete message content.
        """
        await self.broadcast({
            "type": "stream_end",
            "message_id": message_id,
            "content": content,
        })

    async def broadcast_action_result(self, action: str, result: Dict[str, Any]) -> None:
        """Broadcast an action result to all clients.

        Args:
            action: The action that was executed.
            result: The action result data.
        """
        await self.broadcast({
            "type": "action_result",
            "action": action,
            "data": result,
        })

    def make_stream_callback(self) -> Callable:
        """Create a callback for streaming from the bridge.

        Returns:
            An async callable that broadcasts stream events.
        """
        async def callback(data: Dict[str, Any]) -> None:
            await self.broadcast(data)
        return callback

    def make_broadcast_callback(self) -> Callable:
        """Create a callback for CDP snapshot broadcasting.

        Returns:
            An async callable that broadcasts snapshot updates.
        """
        async def callback(data: Dict[str, Any]) -> None:
            await self.broadcast(data)
        return callback

    @property
    def client_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


# Global singleton
ws_manager = ConnectionManager()
