"""
Bridge module between the FastAPI server and Antigravity core.

Provides async wrappers around GeminiAgent, SwarmOrchestrator, and Settings
so the REST/WS layer can interact with the agent system.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings


class AgentBridge:
    """Bridge between the mobile UI server and the Antigravity core.

    Wraps agent and swarm functionality for use by REST/WebSocket handlers.
    """

    def __init__(self) -> None:
        """Initialize the bridge with default state."""
        self._agent = None
        self._swarm = None
        self._current_workspace: str = str(settings.project_root_path)
        self._current_model: str = settings.GEMINI_MODEL_NAME
        self._chat_history: List[Dict[str, Any]] = []
        self._conversation_id: str = ""

    @property
    def current_workspace(self) -> str:
        """Return the current active workspace path."""
        return self._current_workspace

    @property
    def current_model(self) -> str:
        """Return the currently selected model name."""
        return self._current_model

    def set_model(self, model_name: str) -> Dict[str, str]:
        """Update the active model.

        Args:
            model_name: The model identifier to switch to.

        Returns:
            Confirmation dict with the new model name.
        """
        self._current_model = model_name
        settings.GEMINI_MODEL_NAME = model_name
        return {"model": model_name, "status": "updated"}

    def list_workspaces(self) -> List[Dict[str, str]]:
        """List available workspace directories.

        Scans for directories containing AGENTS.md or src/ to identify
        valid Antigravity workspaces.

        Returns:
            List of workspace dicts with name and path.
        """
        workspaces = []
        # Add current project as a workspace
        workspaces.append({
            "name": PROJECT_ROOT.name,
            "path": str(PROJECT_ROOT),
            "active": str(PROJECT_ROOT) == self._current_workspace,
        })
        # Scan sibling directories for other workspaces
        parent = PROJECT_ROOT.parent
        for child in parent.iterdir():
            if child.is_dir() and child != PROJECT_ROOT:
                if (child / "AGENTS.md").exists() or (child / "src").is_dir():
                    workspaces.append({
                        "name": child.name,
                        "path": str(child),
                        "active": str(child) == self._current_workspace,
                    })
        return workspaces

    def set_workspace(self, workspace_path: str) -> Dict[str, str]:
        """Switch the active workspace.

        Args:
            workspace_path: Absolute path to the new workspace.

        Returns:
            Confirmation dict with the new workspace.
        """
        self._current_workspace = workspace_path
        return {"workspace": workspace_path, "status": "updated"}

    def list_models(self) -> List[Dict[str, Any]]:
        """List available AI models.

        Returns:
            List of model option dicts.
        """
        return [
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "google"},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "google"},
            {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash Exp", "provider": "google"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "google"},
            {"id": settings.OPENAI_MODEL, "name": settings.OPENAI_MODEL, "provider": "openai"},
        ]

    def list_agents(self) -> List[Dict[str, Any]]:
        """Discover agents in src/agents/.

        Returns:
            List of agent metadata dicts.
        """
        agents_dir = PROJECT_ROOT / "src" / "agents"
        agents = []
        if agents_dir.exists():
            for f in agents_dir.glob("*.py"):
                if f.name.startswith("_"):
                    continue
                name = f.stem.replace("_agent", "").replace("_", " ").title()
                agents.append({
                    "id": f.stem,
                    "name": name,
                    "file": str(f),
                    "status": "idle",
                })
        return agents

    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a chat message to the agent and get a response.

        Args:
            message: The user's chat message.

        Returns:
            Dict with the agent's response text.
        """
        # Store in history
        self._chat_history.append({
            "role": "user",
            "content": message,
        })

        # For Phase 0, return a simulated response
        # This will be wired to GeminiAgent in Phase 1
        response_text = (
            f"🪐 **Antigravity Agent** received your message: \"{message}\"\n\n"
            f"_Agent bridge is running in Phase 0 mode. "
            f"Full agent integration coming in Phase 1._"
        )

        self._chat_history.append({
            "role": "assistant",
            "content": response_text,
        })

        return {"role": "assistant", "content": response_text}

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Return the current chat history.

        Returns:
            List of message dicts.
        """
        return self._chat_history.copy()

    def list_artifacts(self) -> List[Dict[str, str]]:
        """List artifacts in the artifacts/ directory.

        Returns:
            List of artifact file dicts.
        """
        artifacts_dir = settings.artifacts_path
        artifacts = []
        if artifacts_dir.exists():
            for f in artifacts_dir.rglob("*"):
                if f.is_file() and f.name != ".gitkeep":
                    artifacts.append({
                        "name": f.name,
                        "path": str(f.relative_to(artifacts_dir)),
                        "size": f.stat().st_size,
                    })
        return artifacts


# Global singleton
bridge = AgentBridge()
