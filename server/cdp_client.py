"""
Chrome DevTools Protocol (CDP) client for Antigravity Mobile Connect.

Discovers and connects to a running Antigravity desktop instance via CDP,
captures chat snapshots, and injects messages for remote control.

Phase 1.5: Enables API-key-free chat by mirroring the desktop Antigravity session.
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

# Ports to scan for Antigravity's CDP endpoint
DEFAULT_CDP_PORTS = [9222, 9000, 9001, 9002, 9003]

# JavaScript to extract structured chat messages from Antigravity's DOM
# Updated to handle deep nesting and virtual scrolling wrappers
SNAPSHOT_JS = """
(function() {
    // Helper to get React Fiber node from a DOM element
    function getReactFiber(node) {
        for (const key in node) {
            if (key.startsWith('__reactFiber$')) {
                return node[key];
            }
        }
        return null;
    }

    // Helper to traverse up the Fiber tree to find a specific prop
    function findPropUpwards(fiber, propCheck, limit = 50) {
        let curr = fiber;
        let count = 0;
        while (curr && count < limit) {
            const props = curr.memoizedProps || {};
            if (propCheck(props)) {
                return props;
            }
            curr = curr.return;
            count++;
        }
        return null;
    }

    try {
        // Safe recursive finder with depth limit
        function findAllContainers(doc, results = [], depth = 0) {
            if (depth > 20) return results; // Increased safety limit from 5 to 20

            // Candidates in current doc
            const candidates = [
                doc.getElementById('conversation'),
                doc.getElementById('chat'),
                doc.getElementById('cascade'),
                doc.querySelector('.chat-list'),
                (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null)
            ];
            
            candidates.forEach(c => {
                if (c) results.push(c);
            });

            // Recurse into frames
            const frames = doc.querySelectorAll('iframe, webview');
            for (const frame of frames) {
                try {
                    const innerDoc = frame.contentDocument;
                    if (innerDoc) {
                        findAllContainers(innerDoc, results, depth + 1);
                    }
                } catch(e) {}
            }
            return results;
        }

        const containers = findAllContainers(document);
        if (containers.length === 0) {
            return { error: 'chat_container_not_found', messages: [] };
        }

        // Search ALL containers for the best trajectory (most steps)
        let bestSteps = null;
        let validContainer = null;

        for (const container of containers) {
            let targetNode = container;
            const inner = container.querySelector('div[class*="gap-y-3"]');
            if (inner) targetNode = inner;

            let foundFromContainer = null;

            // Strategy 1: Check the container/inner itself
            let fiber = getReactFiber(targetNode);
            if (fiber) foundFromContainer = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);

            // Strategy 2: Check children
            if (!foundFromContainer && targetNode.children.length > 0) {
                 for (let i=0; i<Math.min(targetNode.children.length, 3); i++) {
                     fiber = getReactFiber(targetNode.children[i]);
                     if (fiber) {
                         foundFromContainer = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
                         if (foundFromContainer) break;
                     }
                 }
            }

            if (foundFromContainer && foundFromContainer.trajectory && foundFromContainer.trajectory.steps) {
                const steps = foundFromContainer.trajectory.steps;
                // If we haven't found any steps yet, or this one has MORE steps, take it.
                if (bestSteps === null || steps.length > bestSteps.length) {
                    bestSteps = steps;
                    validContainer = container;
                }
            }
        }

        if (!bestSteps) {
             return { error: 'trajectory_data_not_found', messages: [] };
        }

        // 3. Extract and Map Messages
        const steps = bestSteps;
        const messages = [];

        // Helper to extract text from potential objects
        const getText = (content) => {
            if (!content) return '';
            if (typeof content === 'string') return content;
            if (content.content) return getText(content.content);
            return JSON.stringify(content);
        };

        steps.forEach((item, index) => {
            // The structure is usually item.step containing the data
            // It might be a Protobuf-like structure with { case: '...', value: ... }
            let step = item.step || item;
            if (step.value) {
                step = step.value;
            }
            
            let id = item.id || step.id || `step-${index}`;
            let role = 'assistant';
            let type = 'text';
            let content = '';

            // --- determine Role & Content via heuristics ---

            // 1. User Message
            // Strictly check for userResponse string first
            if (step.userResponse && typeof step.userResponse === 'string') {
                role = 'user';
                content = step.userResponse;
            } else if (step.query) {
                role = 'user';
                content = getText(step.query);
            } else if (step.activeUserState && step.activeUserState.query) {
                role = 'user';
                content = getText(step.activeUserState.query);
            } else if (step.items && Array.isArray(step.items)) {
                if (!content) {
                     const userItems = step.items.filter(i => i.text || i.content);
                     if (userItems.length > 0) {
                        role = 'user';
                        content = userItems.map(i => getText(i.text || i.content)).join('\\n');
                     }
                }
            }  else if (step.type === 'user_message' || (step.message && step.message.role === 'user')) {
                role = 'user';
                 if (step.content) content = getText(step.content);
                 else if (step.message) content = getText(step.message.content);
            }

            // 2. Assistant Message / Tool Use
            if (!content) {
                // Check for 'notify_user' tool call
                if (step.notificationContent) {
                     content = step.notificationContent;
                     if (step.reviewAbsoluteUris && Array.isArray(step.reviewAbsoluteUris) && step.reviewAbsoluteUris.length > 0) {
                          content += `\\n\\n(Requested review for: ${step.reviewAbsoluteUris.map(p => p.split(/[\\\\/]/).pop()).join(', ')})`;
                     }
                }
                else if (step.name === 'notify_user' && step.argumentsJson) {
                    try {
                        const args = JSON.parse(step.argumentsJson);
                        if (args.Message) {
                            content = args.Message;
                            if (args.PathsToReview && args.PathsToReview.length > 0) {
                                content += `\\n\\n(Requested review for: ${args.PathsToReview.map(p => p.split(/[\\\\/]/).pop()).join(', ')})`;
                            }
                        }
                    } catch (e) {}
                }
            
                // Check 'modifiedResponse' (final edited response)
                else if (step.modifiedResponse) {
                    content = getText(step.modifiedResponse);
                } 
                // Check 'response' (raw response)
                else if (step.response) {
                    content = getText(step.response);
                }
                // Check 'content' directly
                else if (step.content) {
                    content = getText(step.content);
                }
                // Check 'message.content'
                else if (step.message && step.message.content) {
                    content = getText(step.message.content);
                    if (step.message.role) role = step.message.role;
                }
            }

            // 3. Tool Use / Code Execution
            if (step.directoryPathUri || step.searchPathUri || step.commandLine || (step.toolCalls && !content)) {
                // This is a tool step (and not a notify_user we already handled)
                 type = 'tool-use'; 
            }
            
            // 4. Fallback
            if (!content && step.text) {
                content = getText(step.text);
            }

            // --- FILTERING ---
            
            const trimmed = content.trim();

            // Remove internal system messages - Use startsWith to allow users to discuss these tags without being filtered
            if (trimmed.startsWith('<EPHEMERAL_MESSAGE>') || 
                trimmed.startsWith('<artifact_reminder>') || 
                trimmed.startsWith('<active_task_reminder>') ||
                trimmed.startsWith('The following is an <EPHEMERAL_MESSAGE>') ||
                trimmed.startsWith('<knowledge_item>')
               ) {
                return; // Skip this message
            }
            
            // Remove "Conversation History" header block
            if (trimmed.startsWith('# Conversation History') && content.includes('Here are the conversation IDs')) {
                return; // Skip history dump
            }

            // Remove tool-use history dumps (often treated as user messages by heuristics if they contain text)
            if (type === 'tool-use' && content.includes('Conversation History')) {
                return;
            }

            // Remove specific conversation ID lists from tool use or text
            if (trimmed.startsWith('Here are the conversation IDs') ||
                trimmed.startsWith('Here are the') && trimmed.includes('most recently accessed knowledge items') ||
                (trimmed.startsWith('Step Id:') && !trimmed.includes('Phase')) // Allow Phase updates
               ) {
                return;
            }

            if (trimmed) {
                messages.push({
                    id: id,
                    role: role,
                    content: content,
                    type: type,
                    timestamp: item.createdAt || Date.now()
                });
            }
        });

        return {
            messages: messages,
            count: messages.length,
            rawStepCount: steps ? steps.length : 0,
            containerId: validContainer ? validContainer.id : 'unknown'
        };

    } catch (e) {
        return { error: e.toString(), messages: [] };
    }
})()
"""

# JavaScript to inject a message into Antigravity's input field
# Now handles iframes
INJECT_MESSAGE_JS = """
(async () => {{
    function findDocWithInput(rootDoc) {{
        if (rootDoc.querySelector('[contenteditable="true"]')) return rootDoc;
        const frames = rootDoc.querySelectorAll('iframe, webview');
        for (const frame of frames) {{
            try {{
                const doc = frame.contentDocument;
                if (doc && doc.querySelector('[contenteditable="true"]')) return doc;
            }} catch(e) {{}}
        }}
        return null;
    }}

    const targetDoc = findDocWithInput(document);
    if (!targetDoc) return {{ ok: false, error: "input_not_found" }};

    // Check if agent is currently generating
    const cancel = targetDoc.querySelector('[data-tooltip-id="input-send-button-cancel-tooltip"]');
    if (cancel && cancel.offsetParent !== null) return {{ ok: false, reason: "busy" }};

    const editors = [...targetDoc.querySelectorAll(
        '#conversation [contenteditable="true"], '
        + '#chat [contenteditable="true"], '
        + '#cascade [contenteditable="true"], '
        + '[contenteditable="true"]'
    )].filter(el => el.offsetParent !== null);
    
    const editor = editors[editors.length - 1];
    if (!editor) return {{ ok: false, error: "editor_not_found" }};

    const textToInsert = {safe_text};

    editor.focus();
    targetDoc.execCommand && targetDoc.execCommand("selectAll", false, null);
    targetDoc.execCommand && targetDoc.execCommand("delete", false, null);

    let inserted = false;
    try {{
        inserted = !!targetDoc.execCommand && targetDoc.execCommand("insertText", false, textToInsert);
    }} catch(e) {{}}

    if (!inserted) {{
        editor.textContent = textToInsert;
        editor.dispatchEvent(new InputEvent("beforeinput", {{
            bubbles: true, inputType: "insertText", data: textToInsert
        }}));
        editor.dispatchEvent(new InputEvent("input", {{
            bubbles: true, inputType: "insertText", data: textToInsert
        }}));
    }}

    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

    // Try to find submit button
    const submit = targetDoc.querySelector("svg.lucide-arrow-right")
        && targetDoc.querySelector("svg.lucide-arrow-right").closest("button");
    
    if (submit && !submit.disabled) {{
        submit.click();
        return {{ ok: true, method: "click_submit" }};
    }}

    // Fallback: Enter key
    editor.dispatchEvent(new KeyboardEvent("keydown", {{
        bubbles: true, key: "Enter", code: "Enter"
    }}));
    editor.dispatchEvent(new KeyboardEvent("keyup", {{
        bubbles: true, key: "Enter", code: "Enter"
    }}));

    return {{ ok: true, method: "enter_keypress" }};
}})()
"""

# JavaScript to get current app state
APP_STATE_JS = """
(function() {
    function findDocWithText(rootDoc) {
        if (rootDoc.body && rootDoc.body.textContent.includes('Fast')) return rootDoc;
        const frames = rootDoc.querySelectorAll('iframe, webview');
        for (const frame of frames) {
            try {
                const doc = frame.contentDocument;
                if (doc) return doc; // Just take the first valid frame for now
            } catch(e) {}
        }
        return rootDoc;
    }

    try {
        const doc = findDocWithText(document);
        const KNOWN_MODELS = ["Gemini", "Claude", "GPT"];
        const KNOWN_MODES = ["Fast", "Planning"];

        let mode = null;
        let model = null;

        const allEls = Array.from(doc.querySelectorAll('*'));
        for (const el of allEls) {
            if (el.children.length > 0) continue;
            const txt = (el.textContent || '').trim();

            if (!mode && KNOWN_MODES.includes(txt)) mode = txt;
            if (!model) {
                for (const m of KNOWN_MODELS) {
                    if (txt.includes(m)) { model = txt; break; }
                }
            }
            if (mode && model) break;
        }

        const cancelBtn = doc.querySelector(
            '[data-tooltip-id="input-send-button-cancel-tooltip"]'
        );
        const isGenerating = cancelBtn !== null && cancelBtn.offsetParent !== null;

        return { mode, model, isGenerating };
    } catch(e) {
        return { error: e.toString() };
    }
})()
"""

STOP_GENERATION_JS = """
(async () => {
    // Helper to search docs
    function getDocs(root) {
        const docs = [root];
        root.querySelectorAll('iframe, webview').forEach(frame => {
            try { if(frame.contentDocument) docs.push(frame.contentDocument); } catch(e){}
        });
        return docs;
    }

    for (const doc of getDocs(document)) {
        const cancel = doc.querySelector(
            '[data-tooltip-id="input-send-button-cancel-tooltip"]'
        );
        if (cancel && cancel.offsetParent !== null) {
            cancel.click();
            return { success: true };
        }
        
        const stopBtn = doc.querySelector('button svg.lucide-square');
        if (stopBtn) {
            const btn = stopBtn.closest('button');
            if (btn && btn.offsetParent !== null) {
                btn.click();
                return { success: true, method: 'fallback_square' };
            }
        }
    }

    return { error: 'No active generation found to stop' };
})()
"""


async def discover_cdp(
    ports: Optional[List[int]] = None,
    host: str = "localhost",
) -> Optional[str]:
    """Discover Antigravity's CDP WebSocket endpoint.

    Scans ports and returns the WebSocket URL. Prioritizes the 'workbench'
    target (Editor) over 'Launchpad'.
    """
    ports = ports or DEFAULT_CDP_PORTS

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=3)
    ) as session:
        for port in ports:
            try:
                url = f"http://{host}:{port}/json"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        targets = await resp.json()
                        
                        # Filter for valid page targets
                        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
                        
                        if not pages:
                            continue

                        # Prioritize 'workbench.html' (Editor) and exclude 'Launchpad'
                        target = next(
                            (t for t in pages if 
                             "workbench.html" in t.get("url", "") and 
                             "Launchpad" not in t.get("title", "")), 
                            None
                        )

                        
                        logger.info(
                            "Found CDP target on port %d: %s (%s)",
                            port, target.get("title"), target.get("url")
                        )
                        return target.get("webSocketDebuggerUrl")

            except Exception:
                continue

    logger.warning("No CDP endpoint found on ports %s", ports)
    return None


class CDPConnection:
    """Manages a WebSocket connection to a CDP endpoint.

    Provides methods for evaluating JavaScript in the page context,
    capturing snapshots, and injecting messages.
    """

    def __init__(self, ws_url: str) -> None:
        """Initialize the CDP connection.

        Args:
            ws_url: The WebSocket debugger URL from CDP discovery.
        """
        self._ws_url = ws_url
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._msg_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._connected = False
        self._reader_task: Optional[asyncio.Task] = None

    @property
    def connected(self) -> bool:
        """Return whether the CDP connection is active."""
        return self._connected and self._ws is not None and not self._ws.closed

    async def connect(self) -> bool:
        """Establish the CDP WebSocket connection.

        Returns:
            True if connection succeeded.
        """
        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(
                self._ws_url,
                max_msg_size=10 * 1024 * 1024,  # 10MB for large snapshots
            )
            self._connected = True
            self._reader_task = asyncio.create_task(self._read_loop())
            logger.info("CDP connected to %s", self._ws_url)
            return True
        except Exception as e:
            logger.error("CDP connection failed: %s", e)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close the CDP connection."""
        self._connected = False
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        logger.info("CDP disconnected")

    async def _read_loop(self) -> None:
        """Background task to read CDP WebSocket messages."""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_id = data.get("id")
                    if msg_id is not None and msg_id in self._pending:
                        self._pending[msg_id].set_result(data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("CDP read loop error: %s", e)
        finally:
            self._connected = False

    async def send(
        self, method: str, params: Optional[Dict] = None, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Send a CDP command and wait for the response.

        Args:
            method: The CDP method name (e.g., 'Runtime.evaluate').
            params: Optional parameters for the method.
            timeout: Timeout in seconds.

        Returns:
            The CDP response dict.

        Raises:
            RuntimeError: If not connected.
            asyncio.TimeoutError: If the response is not received in time.
        """
        if not self.connected:
            raise RuntimeError("Not connected to CDP")

        self._msg_id += 1
        msg_id = self._msg_id

        message = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future

        await self._ws.send_json(message)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        finally:
            self._pending.pop(msg_id, None)

    async def evaluate(
        self, expression: str, await_promise: bool = False
    ) -> Any:
        """Evaluate a JavaScript expression in the page context.

        Args:
            expression: JavaScript code to evaluate.
            await_promise: If True, await the result if it's a Promise.

        Returns:
            The evaluated result value, or None on error.
        """
        result = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })

        if "error" in result:
            print(f"DEBUG: CDP evaluate error: {result['error']}", flush=True)
            logger.warning("CDP evaluate error: %s", result["error"])
            return None

        value = result.get("result", {}).get("result", {}).get("value")
        # print(f"DEBUG: Evaluate result value type: {type(value)}", flush=True)
        return value

    async def capture_snapshot(self) -> Optional[Dict[str, Any]]:
        """Capture a structured snapshot of the current chat.

        Returns:
            Dict with 'messages' list and metadata, or None on failure.
        """
        if not self.connected:
            return None

        try:
            result = await self.evaluate(SNAPSHOT_JS)
            
            if result and isinstance(result, dict):
                if result.get("error"):
                    logger.debug("Snapshot error: %s", result["error"])
                
                # Post-process messages to fix list formatting
                # "1.\nItem" -> "1. Item"
                if "messages" in result:
                    count = len(result["messages"])
                    logger.debug("Snapshot found %d messages (Raw steps: %s)", count, result.get('rawStepCount', 'N/A'))
                    
                    import re
                    for msg in result["messages"]:
                        content = msg.get("content", "")
                        # Regex to find "Number." followed by newline and non-newline char
                        # We replace newline with space
                        fixed_content = re.sub(r'(?m)^(\d+)\.\n', r'\1. ', content)
                        msg["content"] = fixed_content
                        
                else:
                    print("DEBUG: No 'messages' key in snapshot result")

                return result
            else:
                print(f"DEBUG: Snapshot result is not a dict: {type(result)}")
        except Exception as e:
            print(f"DEBUG: Snapshot Exception: {e}")
            logger.error("Snapshot capture failed: %s", e)


        return None

    async def inject_message(self, text: str) -> Dict[str, Any]:
        """Inject a message into Antigravity's chat input.

        Args:
            text: The message text to send.

        Returns:
            Result dict with 'ok' boolean and method or error.
        """
        if not self.connected:
            return {"ok": False, "error": "not_connected"}

        safe_text = json.dumps(text)
        js = INJECT_MESSAGE_JS.format(safe_text=safe_text)

        try:
            result = await self.evaluate(js, await_promise=True)
            if result:
                return result
            return {"ok": False, "error": "no_result"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_app_state(self) -> Dict[str, Any]:
        """Get the current Antigravity app state (mode, model, generating).

        Returns:
            Dict with mode, model, and isGenerating fields.
        """
        if not self.connected:
            return {"error": "not_connected"}

        try:
            result = await self.evaluate(APP_STATE_JS)
            return result or {"error": "no_result"}
        except Exception as e:
            return {"error": str(e)}

    async def stop_generation(self) -> Dict[str, Any]:
        """Stop the current AI generation in Antigravity.

        Returns:
            Result dict with success or error.
        """
        if not self.connected:
            return {"error": "not_connected"}

        try:
            result = await self.evaluate(STOP_GENERATION_JS, await_promise=True)
            return result or {"error": "no_result"}
        except Exception as e:
            return {"error": str(e)}


def hash_messages(messages: List[Dict]) -> str:
    """Create a short hash of the messages for delta detection.

    Args:
        messages: List of message dicts.

    Returns:
        A hex digest string.
    """
    raw = json.dumps(messages, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()[:12]
