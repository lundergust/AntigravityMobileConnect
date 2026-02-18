# 🏗️ Antigravity Mobile Connect — Architecture

> **System Design & Component Overview**

## 1. High-Level Design

Antigravity Mobile Connect is a client-server application that enables remote control of a desktop AI agent from a mobile device.

It solves the problem of "tethered" AI interaction by bridging the desktop's powerful runtime environment (with file system access, tools, and heavy compute) to a lightweight mobile interface.

### System Diagram

```mermaid
graph TD
    User((User)) -->|Mobile Browser| UI[Mobile UI]
    
    subgraph Desktop Workstation
        subgraph "Bridge Server (FastAPI)"
            API[REST API]
            WS[WebSocket Hub]
            CDP_Client[CDP Bridge]
            Agent_Bridge[Agent Bridge]
        end
        
        subgraph "Antigravity Agent"
            Core[Gemini Agent]
            Chrome[Chrome Instance]
            FileSys[File System]
        end
    end
    
    UI <-->|WebSocket| WS
    UI <-->|HTTP| API
    
    WS --> CDP_Client
    WS --> Agent_Bridge
    
    CDP_Client <-->|DevTools Protocol (9222)| Chrome
    Agent_Bridge <-->|Direct Python Call| Core
    
    Core --> FileSys
    Chrome --> FileSys
```

---

## 2. Core Components

### 2.1. Mobile Frontend (`mobile-ui/`)
- **Tech Stack**: React 19, TypeScript, Vite.
- **Role**: Render the chat interface, visualize artifacts, and send user commands.
- **Key Modules**:
  - `src/hooks/useWebSocket.ts`: Manages the resilient WebSocket connection.
  - `src/components/ChatView.tsx`: Displays the streaming chat history.
  - `src/components/ArtifactViewer.tsx`: Shows file contents and diffs.

### 2.2. Bridge Server (`server/`)
- **Tech Stack**: Python 3.11+, FastAPI, Uvicorn.
- **Role**: Orchestrate communication between mobile and desktop using two modes:

#### Mode A: CDP Mirror (Primary)
- **File**: `server/cdp_client.py`
- **Mechanism**: Connects to the desktop agent's Chrome instance via Remote Debugging Port (9222).
- **Function**: Mirrors the *existing* desktop session.
  - **Reads**: DOM snapshots converted to JSON for history.
  - **Writes**: Injects JavaScript to type into the desktop input box.
- **Benefit**: Zero-config; reuses the desktop's authenticated session.

#### Mode B: Headless Agent (Fallback)
- **File**: `server/bridge.py`
- **Mechanism**: Imports `src.agent.GeminiAgent` directly.
- **Function**: Runs an independent agent instance inside the bridge process.
- **Benefit**: Works without a browser, suitable for server-only deployments.

### 2.3. Agent Core (`src/`)
- **Tech Stack**: Google Gemini SDK, Python.
- **Role**: The "brain" that executes tasks.
- **Structure**:
  - `agent.py`: Main `GeminiAgent` class implementing Think-Act-Reflect loop.
  - `tools/`: Auto-discovered Python functions exposed to the LLM.
  - `memory.py`: Manages conversation context and summarization.

---

## 3. Data Flow

### 3.1. User Sends Message (Mobile -> Desktop)
1. **Mobile**: User types "Analyze budget.csv".
2. **WS**: Sends JSON `{type: "chat_send", message: "Analyze budget.csv"}`.
3. **Bridge**:
   - If CDP connected: Calls `Runtime.evaluate` to inject text into desktop input.
   - If Headless: Calls `agent.act("Analyze budget.csv")`.

### 3.2. Agent Responds (Desktop -> Mobile)
#### a) CDP Mode
1. **Desktop**: Agent generates response tokens in the browser UI.
2. **Bridge**: Polls `server/bridge.py:CDPBridge` every 1s.
   - Captures snapshot of chat DOM.
   - Computes diff against last known state.
3. **WS**: Broadcasts `{type: "snapshot_update", messages: [...]}` to mobile.
4. **Mobile**: Re-renders chat view.

#### b) Headless Mode
1. **Bridge**: `server/bridge.py:AgentBridge` receives tokens from LLM.
2. **WS**: Streams `{type: "stream_chunk", chunk: "..."}` in real-time.
3. **Mobile**: Appends chunks to the active message bubble.

---

## 4. Connectivity Strategy

To access the *local* desktop server from a *mobile* device on a different network:

1. **Local LAN**: Attempts direct IP connection (e.g., `192.168.1.5:8000`). Fast but requires same Wi-Fi.
2. **Tailscale**: Checks for Tailscale IP. Secure, persistent VPN mesh.
3. **ngrok/Tunnel**: Optional fallback. Public URL tunnel (slower, requires setup).

The `start.py` script automatically detects available interfaces and prints the best connection URL/QR code.

---

## 5. Security Model

- **Authentication**: Currently relies on network-level security (LAN/VPN) or obscure tunnel URLs.
- **Plan**: Add token-based auth for public tunnel exposure.
- **Sandboxing**: Agent runs with user privileges on the host machine. (Same risk profile as running a local shell).

---

## 6. Directory Structure

- `mobile-ui/`: Frontend source code.
- `server/`: Backend bridge code.
- `src/`: Core agent implementation.
- `artifacts/`: Generated outputs (plans, code, reports).
- `docs/`: Project documentation.
