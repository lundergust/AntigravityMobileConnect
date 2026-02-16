"""
Chat history persistence routes.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from server.bridge import bridge

router = APIRouter(prefix="/api/history", tags=["history"])

# Store history in artifacts/chat_history/
HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "chat_history"


def _ensure_dir() -> None:
    """Create the history directory if it doesn't exist."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/")
async def list_conversations() -> List[Dict[str, Any]]:
    """List saved conversations.

    Returns:
        List of conversation summary dicts.
    """
    _ensure_dir()
    conversations = []
    for f in sorted(HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            conversations.append({
                "id": f.stem,
                "title": data.get("title", "Untitled"),
                "created_at": data.get("created_at", ""),
                "message_count": len(data.get("messages", [])),
                "preview": data.get("messages", [{}])[0].get("content", "")[:80] if data.get("messages") else "",
            })
        except (json.JSONDecodeError, IndexError):
            continue
    return conversations


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """Load a specific conversation.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        Full conversation data dict.

    Raises:
        HTTPException: If conversation not found.
    """
    _ensure_dir()
    filepath = HISTORY_DIR / f"{conversation_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    return json.loads(filepath.read_text(encoding="utf-8"))


@router.post("/save")
async def save_conversation(payload: Dict[str, Any]) -> Dict[str, str]:
    """Save a chat session to history.

    Accepts messages from the client. Falls back to bridge history
    when no messages are provided.

    Args:
        payload: Dict with optional "title" and "messages" keys.

    Returns:
        Dict with the saved conversation ID.
    """
    _ensure_dir()

    messages = payload.get("messages", [])
    if not messages:
        messages = bridge.get_chat_history()

    # Don't save empty conversations
    if not messages:
        return {"id": "", "status": "empty"}

    # Auto-generate title from first user message if not provided
    title = payload.get("title", "")
    if not title:
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                title = content[:60] + ("..." if len(content) > 60 else "")
                break
        if not title:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    conv_id = str(uuid.uuid4())
    data = {
        "id": conv_id,
        "title": title,
        "created_at": datetime.now().isoformat(),
        "messages": messages,
    }
    filepath = HISTORY_DIR / f"{conv_id}.json"
    filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"id": conv_id, "status": "saved"}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> Dict[str, str]:
    """Delete a conversation.

    Args:
        conversation_id: UUID of the conversation.

    Returns:
        Confirmation dict.

    Raises:
        HTTPException: If conversation not found.
    """
    _ensure_dir()
    filepath = HISTORY_DIR / f"{conversation_id}.json"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    filepath.unlink()
    return {"id": conversation_id, "status": "deleted"}
