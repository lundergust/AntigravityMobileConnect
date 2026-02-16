"""
Workspace and model selection routes.
"""

from typing import Any, Dict

from fastapi import APIRouter

from server.bridge import bridge

router = APIRouter(prefix="/api", tags=["workspace"])


@router.get("/workspaces")
async def list_workspaces():
    """List available workspaces/repositories.

    Returns:
        List of workspace dicts.
    """
    return bridge.list_workspaces()


@router.post("/workspace/select")
async def select_workspace(payload: Dict[str, Any]) -> Dict[str, str]:
    """Switch the active workspace.

    Args:
        payload: Dict with "path" key.

    Returns:
        Confirmation dict.
    """
    path = payload.get("path", "")
    return bridge.set_workspace(path)


@router.get("/models")
async def list_models():
    """List available AI models.

    Returns:
        List of model dicts.
    """
    return bridge.list_models()


@router.post("/model/select")
async def select_model(payload: Dict[str, Any]) -> Dict[str, str]:
    """Switch the active model.

    Args:
        payload: Dict with "model" key.

    Returns:
        Confirmation dict.
    """
    model = payload.get("model", "")
    return bridge.set_model(model)
