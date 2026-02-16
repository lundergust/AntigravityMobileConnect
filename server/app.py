"""
FastAPI application factory for the Antigravity Mobile Connect bridge server.

Serves the mobile UI, REST API, and WebSocket endpoints.
"""

import os
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.ws_hub import ws_manager
from server.routes import chat, workspace, agents, quota, history


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="Antigravity Mobile Connect",
        description="Mobile bridge server for the Antigravity Agent Manager",
        version="0.1.0",
    )

    # CORS — allow all origins for mobile access via tunnel
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(chat.router)
    app.include_router(workspace.router)
    app.include_router(agents.router)
    app.include_router(quota.router)
    app.include_router(history.router)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Main WebSocket endpoint for real-time mobile communication."""
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_personal({"type": "pong"}, websocket)
                elif msg_type == "chat_message":
                    from server.bridge import bridge
                    message = data.get("message", "")
                    response = await bridge.send_message(message)
                    await ws_manager.broadcast({
                        "type": "chat_response",
                        "data": response,
                    })
                else:
                    await ws_manager.send_personal({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }, websocket)
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)

    # Health check
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint.

        Returns:
            Status dict with connection count.
        """
        return {
            "status": "ok",
            "clients": ws_manager.client_count,
            "version": "0.1.0",
        }

    # Serve built mobile UI if available
    dist_dir = PROJECT_ROOT / "mobile-ui" / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app


app = create_app()
