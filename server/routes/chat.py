"""
Chat routes for the Antigravity Mobile Connect bridge.

Handles sending messages, streaming responses, and chat actions.
"""

from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.bridge import bridge
from server.ws_hub import ws_manager

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/send")
async def send_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a chat message to the agent.

    Args:
        payload: Dict with a "message" key.

    Returns:
        Agent response dict.
    """
    message = payload.get("message", "")
    response = await bridge.send_message(message)

    # Broadcast to all connected WebSocket clients
    await ws_manager.broadcast({
        "type": "chat_message",
        "data": response,
    })

    return response


@router.get("/history")
async def get_chat_history():
    """Return the current session chat history.

    Returns:
        List of message dicts.
    """
    return bridge.get_chat_history()


@router.post("/action")
async def chat_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a chat action (Run, Reject, Expand, etc.).

    Args:
        payload: Dict with "action" and optional "params" keys.

    Returns:
        Action result dict.
    """
    action = payload.get("action", "")
    params = payload.get("params", {})

    # Phase 0: acknowledge the action
    return {
        "action": action,
        "status": "acknowledged",
        "message": f"Action '{action}' received. Full implementation in Phase 1.",
    }
