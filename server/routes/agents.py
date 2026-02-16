"""
Agent discovery and deployment routes.
"""

from typing import Any, Dict

from fastapi import APIRouter

from server.bridge import bridge

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/")
async def list_agents():
    """Discover agents in the repository.

    Returns:
        List of agent metadata dicts.
    """
    return bridge.list_agents()


@router.post("/{agent_id}/deploy")
async def deploy_agent(agent_id: str, payload: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Deploy a specific agent.

    Args:
        agent_id: The agent module stem name.
        payload: Optional task parameters.

    Returns:
        Deployment status dict.
    """
    return {
        "agent": agent_id,
        "status": "queued",
        "message": f"Agent '{agent_id}' deployment queued. Full implementation in Phase 4.",
    }


@router.post("/swarm/deploy")
async def deploy_swarm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Launch a swarm deployment.

    Args:
        payload: Dict with "task" key describing the swarm task.

    Returns:
        Swarm deployment status dict.
    """
    task = payload.get("task", "")
    return {
        "status": "queued",
        "task": task,
        "message": "Swarm deployment queued. Full implementation in Phase 4.",
    }
