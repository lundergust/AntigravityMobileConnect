"""
FastAPI application factory for the Antigravity Mobile Connect bridge server.

Serves the mobile UI, REST API, and WebSocket endpoints.
Phase 1.5: Added CDP Mirror support for API-key-free chat.
"""

import os
import sys
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup and shutdown.

    On startup: Attempts CDP connection to Antigravity and starts polling.
    On shutdown: Stops polling and disconnects CDP.
    """
    # --- Startup ---
    from server.bridge import cdp_bridge

    cdp_port = int(os.environ.get("CDP_PORT", "9222"))
    print(f"\n🔍 Scanning for Antigravity on CDP port {cdp_port}...")

    connected = await cdp_bridge.connect(port=cdp_port)
    if connected:
        # Start background polling — broadcasts snapshots via ws_manager
        callback = ws_manager.make_broadcast_callback()
        await cdp_bridge.start_polling(callback)
        print("📡 CDP polling started (1s interval)")
    else:
        print("📝 Running in agent-only mode (no CDP connection)")
        print("   To enable CDP: launch Antigravity with --remote-debugging-port=9222")

    yield

    # --- Shutdown ---
    print("\n🛑 Shutting down CDP connection...")
    await cdp_bridge.disconnect()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="Antigravity Mobile Connect",
        description="Mobile bridge server for the Antigravity Agent Manager",
        version="0.2.0",
        lifespan=lifespan,
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
        """Main WebSocket endpoint for real-time mobile communication.

        Supports message types:
        - ping: Health check
        - chat_send: Send a message (routes to CDP or agent)
        - action: Execute a command (Run/Reject/Expand)
        - stop_generation: Stop the current AI generation (CDP only)
        - get_changes: Fetch pending file changes
        - get_artifacts: Fetch artifact list
        - get_cdp_status: Get CDP connection status
        """
        await ws_manager.connect(websocket)

        # Send CDP status immediately on connect
        from server.bridge import cdp_bridge
        await ws_manager.send_personal({
            "type": "cdp_status",
            "data": cdp_bridge.get_status(),
        }, websocket)

        # If CDP has cached messages, send them immediately
        if cdp_bridge.connected and cdp_bridge.last_messages:
            await ws_manager.send_personal({
                "type": "snapshot_update",
                "messages": [
                    {
                        "id": f"cdp-{i}",
                        "role": msg.get("role", "assistant"),
                        "content": msg.get("content", ""),
                    }
                    for i, msg in enumerate(cdp_bridge.last_messages)
                ],
                "count": len(cdp_bridge.last_messages),
            }, websocket)

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_personal({"type": "pong"}, websocket)

                elif msg_type == "chat_send":
                    from server.bridge import bridge, cdp_bridge
                    message = data.get("message", "")

                    if cdp_bridge.connected:
                        # Route to CDP — inject message into desktop Antigravity
                        result = await cdp_bridge.send_message(message)
                        await ws_manager.send_personal({
                            "type": "cdp_inject_result",
                            "data": result,
                        }, websocket)
                    else:
                        # Fallback to agent mode
                        if bridge.is_processing:
                            await ws_manager.send_personal({
                                "type": "error",
                                "message": "Agent is busy processing another message.",
                            }, websocket)
                            continue

                        try:
                            callback = ws_manager.make_stream_callback()
                            await bridge.send_message_streaming(message, callback)
                        except Exception as e:
                            error_id = f"err-{id(e)}"
                            await ws_manager.broadcast({
                                "type": "stream_start",
                                "message_id": error_id,
                            })
                            await ws_manager.broadcast({
                                "type": "stream_end",
                                "message_id": error_id,
                                "content": f"⚠️ **Server Error**\n\n```\n{str(e)}\n```",
                            })

                elif msg_type == "stop_generation":
                    from server.bridge import cdp_bridge
                    if cdp_bridge.connected:
                        result = await cdp_bridge.stop_generation()
                        await ws_manager.send_personal({
                            "type": "stop_result",
                            "data": result,
                        }, websocket)
                    else:
                        await ws_manager.send_personal({
                            "type": "error",
                            "message": "Stop generation requires CDP connection",
                        }, websocket)

                elif msg_type == "get_cdp_status":
                    from server.bridge import cdp_bridge
                    status = cdp_bridge.get_status()
                    if cdp_bridge.connected:
                        app_state = await cdp_bridge.get_app_state()
                        status["app_state"] = app_state
                    await ws_manager.send_personal({
                        "type": "cdp_status",
                        "data": status,
                    }, websocket)

                elif msg_type == "action":
                    from server.bridge import bridge
                    action = data.get("action", "")
                    params = data.get("params", {})
                    result = bridge.execute_action(action, params)
                    await ws_manager.broadcast_action_result(action, result)

                elif msg_type == "get_changes":
                    from server.bridge import bridge
                    changes = bridge.get_pending_changes()
                    await ws_manager.send_personal({
                        "type": "changes_update",
                        "data": changes,
                    }, websocket)

                elif msg_type == "get_artifacts":
                    from server.bridge import bridge
                    artifacts = bridge.list_artifacts()
                    await ws_manager.send_personal({
                        "type": "artifacts_list",
                        "data": artifacts,
                    }, websocket)

                # Legacy support for Phase 0 clients
                elif msg_type == "chat_message":
                    from server.bridge import bridge
                    message = data.get("message", "")
                    callback = ws_manager.make_stream_callback()
                    await bridge.send_message_streaming(message, callback)

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
        """Health check endpoint with CDP status.

        Returns:
            Status dict with connection info.
        """
        from server.bridge import cdp_bridge
        return {
            "status": "ok",
            "clients": ws_manager.client_count,
            "version": "0.2.0",
            "cdp": cdp_bridge.get_status(),
        }

    # CDP management endpoints
    @app.get("/api/cdp/status")
    async def cdp_status():
        """Get CDP connection status and app state."""
        from server.bridge import cdp_bridge
        status = cdp_bridge.get_status()
        if cdp_bridge.connected:
            status["app_state"] = await cdp_bridge.get_app_state()
        return status

    @app.post("/api/cdp/reconnect")
    async def cdp_reconnect():
        """Attempt to reconnect to Antigravity via CDP."""
        from server.bridge import cdp_bridge
        success = await cdp_bridge.reconnect()
        if success:
            callback = ws_manager.make_broadcast_callback()
            await cdp_bridge.start_polling(callback)
        return {
            "success": success,
            "status": cdp_bridge.get_status(),
        }

    @app.post("/api/cdp/stop")
    async def cdp_stop_generation():
        """Stop the current AI generation via CDP."""
        from server.bridge import cdp_bridge
        return await cdp_bridge.stop_generation()

    # Serve built mobile UI if available
    dist_dir = PROJECT_ROOT / "mobile-ui" / "dist"
    if dist_dir.exists():
        print(f"📂 Serving static files from: {dist_dir.resolve()}")
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
    else:
        print(f"⚠️  Static files NOT found at: {dist_dir.resolve()}")

    return app


app = create_app()
