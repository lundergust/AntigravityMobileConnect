"""
Bridge module between the FastAPI server and Antigravity core.

Provides async wrappers around GeminiAgent, SwarmOrchestrator, and Settings
so the REST/WS layer can interact with the agent system.

Phase 1: Real agent integration with simulated streaming.
"""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings


class AgentBridge:
    """Bridge between the mobile UI server and the Antigravity core.

    Wraps agent and swarm functionality for use by REST/WebSocket handlers.
    Phase 1 wires the real GeminiAgent with async execution and simulated streaming.
    """

    def __init__(self) -> None:
        """Initialize the bridge with default state."""
        self._agent = None
        self._swarm = None
        self._current_workspace: str = str(settings.project_root_path)
        self._current_model: str = settings.GEMINI_MODEL_NAME
        self._chat_history: List[Dict[str, Any]] = []
        self._conversation_id: str = ""
        self._is_processing: bool = False
        self._stream_callback: Optional[Callable] = None

    def _get_agent(self):
        """Lazy-initialize the GeminiAgent on first use.

        Returns:
            A GeminiAgent instance.
        """
        if self._agent is None:
            try:
                from src.agent import GeminiAgent
                self._agent = GeminiAgent()
            except Exception as e:
                print(f"⚠️ Failed to initialize GeminiAgent: {e}")
                self._agent = None
        return self._agent

    @property
    def current_workspace(self) -> str:
        """Return the current active workspace path."""
        return self._current_workspace

    @property
    def current_model(self) -> str:
        """Return the currently selected model name."""
        return self._current_model

    @property
    def is_processing(self) -> bool:
        """Return whether the agent is currently processing a message."""
        return self._is_processing

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

    def _run_agent_sync(self, message: str) -> str:
        """Run the agent synchronously (called via to_thread).

        Args:
            message: The user's chat message.

        Returns:
            The agent's response text.
        """
        agent = self._get_agent()
        if agent is None:
            return (
                "⚠️ **Agent Unavailable**\n\n"
                "The GeminiAgent could not be initialized. "
                "Check your API keys and configuration.\n\n"
                "_Ensure `GEMINI_API_KEY` is set in your `.env` file._"
            )
        try:
            result = agent.act(message)
            return result if result else "_(No response from agent)_"
        except Exception as e:
            return f"⚠️ **Agent Error**\n\n```\n{str(e)}\n```"

    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a chat message to the agent and get a response.

        Wraps the synchronous GeminiAgent.act() in asyncio.to_thread()
        so the FastAPI event loop isn't blocked.

        Args:
            message: The user's chat message.

        Returns:
            Dict with the agent's response and metadata.
        """
        # Store user message in history
        message_id = str(uuid.uuid4())[:8]
        self._chat_history.append({
            "id": f"user-{message_id}",
            "role": "user",
            "content": message,
        })

        self._is_processing = True
        try:
            # Run agent in a thread to avoid blocking the event loop
            response_text = await asyncio.to_thread(self._run_agent_sync, message)
        finally:
            self._is_processing = False

        response_id = f"asst-{message_id}"
        response = {
            "id": response_id,
            "role": "assistant",
            "content": response_text,
        }
        self._chat_history.append(response)
        return response

    async def send_message_streaming(
        self, message: str, stream_callback: Callable
    ) -> Dict[str, Any]:
        """Send a message and simulate streaming the response.

        Runs the full agent response, then emits it in chunks via the callback
        to create a streaming visual effect on the client.

        Args:
            message: The user's chat message.
            stream_callback: Async callable(chunk_data) for each chunk.

        Returns:
            Complete response dict.
        """
        message_id = str(uuid.uuid4())[:8]
        response_id = f"asst-{message_id}"

        self._chat_history.append({
            "id": f"user-{message_id}",
            "role": "user",
            "content": message,
        })

        # Signal stream start
        await stream_callback({
            "type": "stream_start",
            "message_id": response_id,
        })

        self._is_processing = True
        try:
            # Timeout after 120 seconds to prevent indefinite hangs
            response_text = await asyncio.wait_for(
                asyncio.to_thread(self._run_agent_sync, message),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            response_text = (
                "⚠️ **Request Timed Out**\n\n"
                "The agent took too long to respond (>120s). "
                "This may be due to a slow API connection or a complex query.\n\n"
                "_Try a simpler message or check your network connection._"
            )
        except Exception as e:
            response_text = f"⚠️ **Unexpected Error**\n\n```\n{str(e)}\n```"
        finally:
            self._is_processing = False

        # Simulate streaming by emitting chunks
        chunk_size = 12  # characters per chunk
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            await stream_callback({
                "type": "stream_chunk",
                "message_id": response_id,
                "chunk": chunk,
            })
            await asyncio.sleep(0.02)  # 20ms between chunks for smooth streaming

        # Signal stream end
        await stream_callback({
            "type": "stream_end",
            "message_id": response_id,
            "content": response_text,
        })

        response = {
            "id": response_id,
            "role": "assistant",
            "content": response_text,
        }
        self._chat_history.append(response)
        return response

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Return the current chat history.

        Returns:
            List of message dicts.
        """
        return self._chat_history.copy()

    def execute_action(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute an agent action (Run, Reject, Expand, etc.).

        Args:
            action: The action identifier.
            params: Optional parameters for the action.

        Returns:
            Action result dict.
        """
        params = params or {}

        if action == "run":
            return {
                "action": "run",
                "status": "executed",
                "message": "Command execution triggered.",
            }
        elif action == "reject":
            return {
                "action": "reject",
                "status": "executed",
                "message": "Command rejected.",
            }
        elif action == "expand_all":
            return {
                "action": "expand_all",
                "status": "executed",
                "message": "All sections expanded.",
            }
        elif action == "collapse_all":
            return {
                "action": "collapse_all",
                "status": "executed",
                "message": "All sections collapsed.",
            }
        else:
            return {
                "action": action,
                "status": "unknown",
                "message": f"Unknown action: {action}",
            }

    def get_pending_changes(self) -> Dict[str, Any]:
        """Get pending file changes in the current workspace via git diff.

        Returns:
            Dict with list of changed files and their status.
        """
        workspace = Path(self._current_workspace)

        # Check if workspace is a git repo
        if not (workspace / ".git").exists():
            return {
                "has_git": False,
                "files": [],
                "message": "No git repository detected in current workspace.",
            }

        try:
            # Get list of changed files
            result = subprocess.run(
                ["git", "diff", "--name-status", "HEAD"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Also get untracked files
            untracked_result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=10,
            )

            files = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status_code, filepath = parts
                    status_map = {
                        "M": "modified",
                        "A": "added",
                        "D": "deleted",
                        "R": "renamed",
                    }
                    files.append({
                        "path": filepath,
                        "status": status_map.get(status_code[0], "unknown"),
                        "status_code": status_code,
                    })

            for line in untracked_result.stdout.strip().split("\n"):
                if line.strip():
                    files.append({
                        "path": line.strip(),
                        "status": "untracked",
                        "status_code": "?",
                    })

            return {
                "has_git": True,
                "files": files,
                "total": len(files),
            }

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {
                "has_git": True,
                "files": [],
                "message": f"Error running git: {str(e)}",
            }

    def get_file_diff(self, file_path: str) -> Dict[str, Any]:
        """Get the unified diff for a specific file.

        Args:
            file_path: Relative path to the file in the workspace.

        Returns:
            Dict with the diff content.
        """
        workspace = Path(self._current_workspace)
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD", "--", file_path],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "file": file_path,
                "diff": result.stdout,
                "has_diff": bool(result.stdout.strip()),
            }
        except Exception as e:
            return {
                "file": file_path,
                "diff": "",
                "has_diff": False,
                "error": str(e),
            }

    def review_change(self, file_path: str, action: str) -> Dict[str, Any]:
        """Approve or reject changes for a specific file.

        Args:
            file_path: Relative path to the file.
            action: 'approve' or 'reject'.

        Returns:
            Result dict.
        """
        workspace = Path(self._current_workspace)

        if action == "approve":
            # Stage the file
            try:
                subprocess.run(
                    ["git", "add", file_path],
                    cwd=str(workspace),
                    capture_output=True,
                    timeout=10,
                )
                return {"file": file_path, "action": "approve", "status": "staged"}
            except Exception as e:
                return {"file": file_path, "action": "approve", "status": "error", "message": str(e)}

        elif action == "reject":
            # Restore the file
            try:
                subprocess.run(
                    ["git", "checkout", "--", file_path],
                    cwd=str(workspace),
                    capture_output=True,
                    timeout=10,
                )
                return {"file": file_path, "action": "reject", "status": "restored"}
            except Exception as e:
                return {"file": file_path, "action": "reject", "status": "error", "message": str(e)}

        return {"file": file_path, "action": action, "status": "unknown"}

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

    def get_artifact_content(self, artifact_path: str) -> Dict[str, Any]:
        """Read the content of an artifact file.

        Args:
            artifact_path: Relative path within the artifacts directory.

        Returns:
            Dict with the artifact content and metadata.
        """
        artifacts_dir = settings.artifacts_path
        full_path = artifacts_dir / artifact_path

        if not full_path.exists():
            return {"error": "Artifact not found", "path": artifact_path}

        # Determine if it's a text file
        text_extensions = {".md", ".txt", ".json", ".py", ".js", ".ts", ".tsx", ".css", ".html", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sh", ".bat"}
        is_text = full_path.suffix.lower() in text_extensions

        if is_text:
            try:
                content = full_path.read_text(encoding="utf-8")
                return {
                    "path": artifact_path,
                    "name": full_path.name,
                    "content": content,
                    "type": "text",
                    "size": full_path.stat().st_size,
                }
            except Exception as e:
                return {"error": str(e), "path": artifact_path}
        else:
            return {
                "path": artifact_path,
                "name": full_path.name,
                "content": None,
                "type": "binary",
                "size": full_path.stat().st_size,
            }


# Global singletons
bridge = AgentBridge()


class CDPBridge:
    """Bridge between the mobile UI and a running Antigravity desktop via CDP.

    Connects to Antigravity's Chrome DevTools Protocol debug port,
    polls for chat snapshots, and injects messages remotely.
    No API key required — the desktop handles all AI processing.

    Phase 1.5 implementation.
    """

    def __init__(self) -> None:
        """Initialize the CDP bridge."""
        self._connection = None
        self._polling_task: Optional[asyncio.Task] = None
        self._stream_callback: Optional[Callable] = None
        self._last_hash: str = ""
        self._last_messages: List[Dict[str, Any]] = []
        self._message_history: List[Dict[str, Any]] = []  # Cumulative history
        self._connected: bool = False
        self._cdp_port: int = 9222

    @property
    def connected(self) -> bool:
        """Return whether CDP is connected to Antigravity."""
        return self._connection is not None and self._connection.connected

    @property
    def last_messages(self) -> List[Dict[str, Any]]:
        """Return the latest captured chat messages."""
        return self._message_history

    async def connect(self, port: Optional[int] = None) -> bool:
        """Discover and connect to Antigravity's CDP endpoint.

        Args:
            port: Override the default CDP port to scan.

        Returns:
            True if connection succeeded.
        """
        from server.cdp_client import discover_cdp, CDPConnection

        if port:
            self._cdp_port = port

        ports = [self._cdp_port] + [
            p for p in [9222, 9000, 9001, 9002, 9003] if p != self._cdp_port
        ]

        ws_url = await discover_cdp(ports=ports)
        if not ws_url:
            print("⚠️  No Antigravity instance found on CDP ports")
            self._connected = False
            return False

        self._connection = CDPConnection(ws_url)
        success = await self._connection.connect()
        self._connected = success

        if success:
            print(f"✅ CDP connected to Antigravity")
        else:
            print("❌ CDP connection failed")

        return success

    async def disconnect(self) -> None:
        """Disconnect from the CDP endpoint and stop polling."""
        await self.stop_polling()
        if self._connection:
            await self._connection.disconnect()
            self._connection = None
        self._connected = False

    async def reconnect(self) -> bool:
        """Attempt to reconnect to Antigravity."""
        await self.disconnect()
        return await self.connect(self._cdp_port)

    async def start_polling(self, callback: Callable) -> None:
        """Start the background polling loop for chat snapshots.

        Args:
            callback: Async callable(data) to broadcast snapshot updates.
        """
        self._stream_callback = callback
        if self._polling_task and not self._polling_task.done():
            return  # Already polling

        self._polling_task = asyncio.create_task(self._poll_loop())

    async def stop_polling(self) -> None:
        """Stop the background polling loop."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

    async def _poll_loop(self) -> None:
        """Background task: poll for chat snapshots every 1s."""
        from server.cdp_client import hash_messages

        while True:
            try:
                if not self.connected:
                    # Try to reconnect
                    reconnected = await self.connect(self._cdp_port)
                    if not reconnected:
                        await asyncio.sleep(5)  # Wait longer before retrying
                        continue

                # print("DEBUG: Calling capture_snapshot...", flush=True) 
                snapshot = await self._connection.capture_snapshot()
                # print("DEBUG: capture_snapshot returned", flush=True)
                
                # DEBUG LOGGING
                if "error" in snapshot:
                    print(f"[CDPBridge] Snapshot Error: {snapshot['error']}")
                elif "messages" in snapshot:
                    # Only print if count changes or periodically to avoid spam
                    if len(snapshot["messages"]) != len(self._message_history):
                         print(f"[CDPBridge] Got new snapshot with {len(snapshot['messages'])} messages (Current history: {len(self._message_history)})")

                if not snapshot or "messages" not in snapshot:
                    await asyncio.sleep(1)
                    continue

                messages = snapshot["messages"]
                
                # --- Merge Logic ---
                # 1. Update existing messages in history (content updates, etc.)
                # 2. Append new messages that are not in history
                
                # Create a lookup for current snapshot messages
                snapshot_map = {m["id"]: m for m in messages if "id" in m}
                
                # Set of IDs currently in history
                history_ids = set()
                
                # Update existing
                for msg in self._message_history:
                    msg_id = msg.get("id")
                    history_ids.add(msg_id)
                    if msg_id in snapshot_map:
                        # Update content, role, type
                        new_msg = snapshot_map[msg_id]
                        msg["content"] = new_msg.get("content", msg["content"])
                        msg["role"] = new_msg.get("role", msg["role"])
                        msg["type"] = new_msg.get("type", msg.get("type", "text"))

                # Append new
                new_items = []
                for msg in messages:
                    if msg.get("id") not in history_ids:
                        self._message_history.append(msg)
                        new_items.append(msg)
                
                # Broadcast to connected clients (sending FULL history for now to be safe)
                if self._stream_callback:
                    await self._stream_callback({
                        "type": "snapshot_update",
                        "messages": [
                            {
                                "id": msg.get("id", f"cdp-{i}"),
                                "role": msg.get("role", "assistant"),
                                "content": msg.get("content", ""),
                                "type": msg.get("type", "text"),
                            }
                            for i, msg in enumerate(self._message_history)
                        ],
                        "count": len(self._message_history),
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️  CDP poll error: {e}")
                import traceback
                traceback.print_exc()

            await asyncio.sleep(1.0)

    async def send_message(self, text: str) -> Dict[str, Any]:
        """Send a message to Antigravity by injecting it via CDP.

        Args:
            text: Message text to send.

        Returns:
            Result dict from CDP injection.
        """
        if not self.connected:
            return {"ok": False, "error": "CDP not connected"}

        return await self._connection.inject_message(text)

    async def get_app_state(self) -> Dict[str, Any]:
        """Get the current Antigravity app state.

        Returns:
            Dict with mode, model, isGenerating.
        """
        if not self.connected:
            return {"error": "CDP not connected"}

        return await self._connection.get_app_state()

    async def stop_generation(self) -> Dict[str, Any]:
        """Stop the current AI generation in Antigravity.

        Returns:
            Result dict.
        """
        if not self.connected:
            return {"error": "CDP not connected"}

        return await self._connection.stop_generation()

    def get_status(self) -> Dict[str, Any]:
        """Get the CDP bridge status.

        Returns:
            Status dict with connection info and message count.
        """
        return {
            "connected": self.connected,
            "port": self._cdp_port,
            "message_count": len(self._last_messages),
            "last_hash": self._last_hash,
        }


# Global CDP bridge singleton
cdp_bridge = CDPBridge()
