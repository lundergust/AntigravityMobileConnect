# Antigravity Mobile Connect — Implementation Plan & Change Log

> **Goal:** Build a mobile-first web client that gives full remote control over the Antigravity agent manager running on the user's PC, accessible via QR code over ngrok or tailored network solutions.

## Architecture Overview

```mermaid
graph TB
    subgraph Phone["📱 Phone Browser"]
        UI["Vite + React SPA<br/>(mobile-first PWA)"]
    end

    subgraph PC["🖥️ User's PC"]
        subgraph Bridge["FastAPI Bridge Server"]
            WS["WebSocket Hub"]
            REST["REST API"]
            QR["QR Code Generator"]
            CDP["CDP Bridge (Chrome Protocol)"]
        end
        subgraph Core["Antigravity Core"]
            Agent["src/agent.py<br/>GeminiAgent"]
            Swarm["src/swarm.py<br/>SwarmOrchestrator"]
            Config["src/config.py<br/>Settings"]
            Tools["src/tools/*"]
            Agents["src/agents/*"]
        end
    end

    subgraph Tunnel["🌐 Tunnel Layer"]
        Ngrok["ngrok (Auto-tunnel)"]
        TS["Tailscale (Mesh VPN)"]
        Local["Local LAN (Wi-Fi)"]
    end

    UI <-->|WebSocket + REST| Tunnel
    Tunnel <--> Bridge
    Bridge <-->|Direct Call| Core
    Bridge <-->|Chrome DevTools Protocol (9222)| PC
```

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Mobile UI** | Vite + React + TypeScript | Fast HMR, tree-shaking, modern DX |
| **Styling** | Vanilla CSS + CSS Variables | Modular, theme-aware, no framework lock-in |
| **Backend** | FastAPI + `uvicorn` | Async-native, WebSocket support, seamless Python integration |
| **Real-time** | WebSocket (native) | Bi-directional streaming for chat and control |
| **Bridge** | CDP (Chrome DevTools Protocol) | "No API Key" integration by mirroring desktop session |
| **Tunnel** | ngrok / Tailscale | Secure remote access from any network |

---

## Change Log & Status

### ✅ Phase 0: Foundation & Server Setup
**Completed**: Initial server scaffold, `start.py` launcher, basic React shell, and connectivity detection (Local/Tailscale/Ngrok).

### ✅ Phase 1: Chat Interface (Core)
**Completed**: Functional chat UI with real-time streaming, command execution (Run/Reject), and artifact viewing.
- **Features**: Markdown rendering, code highlighting, collapsible thought blocks.
- **Fixes**: Mobile styling, input handling, auto-scroll behavior.

### ✅ Phase 1.5: CDP Mirror (No-API-Key Mode)
**Completed**: Seamless integration with running desktop Antigravity instance.
- **CDP Bridge**: Connects to port 9222 to read/write to the desktop agent.
- **State Mirroring**: Polls for chat snapshots and broadcasts to mobile.
- **Remote Control**: Allows stopping generation and injecting user messages.
- **Benefit**: Users don't need to configure a separate API key for the mobile app; it reuses the desktop session.

### 🚧 Phase 2: Workspace & Model Selection [IN PROGRESS]
**Goal**: Allow switching active workspaces and AI models remotely.
- [ ] **Backend**: Endpoints to list/select workspaces and models.
- [ ] **Frontend**: WorkspaceSelector and ModelSelector components.
- [ ] **State Sync**: Persist selection across reloads.

### 📅 Phase 3: Advanced Chat History
**Goal**: Persistent, searchable chat history.
- [ ] **Storage**: Save conversations to `artifacts/chat_history/*.json`.
- [ ] **UI**: History drawer with search and delete functionality.
- [ ] **Resume**: Ability to load past conversations into context.

### 📅 Phase 4: Agent Deployment & Swarms
**Goal**: Orchestrate multi-agent swarms from the phone.
- [ ] **Discovery**: Auto-detect `src/agents/*.py`.
- [ ] **Control**: Start/Stop/Monitor individual agents.
- [ ] **Visualizer**: Real-time status of swarm workers.

### 📅 Phase 5: Quota Cockpit
**Goal**: Visual dashboard for token usage and costs.
- [ ] **Metrics**: Track input/output tokens per model.
- [ ] **Dashboard**: Guages and charts for "Burn Rate" and "Remaining Budget".
- [ ] **Alerts**: Push notifications for low balance.

---

## Active Tasks

| Task | Status | Priority |
|------|--------|----------|
| **Documentation Overhaul** | 🔄 In Progress | High |
| **Fix Scroll Glitches** | 🐛 Investigating | Medium |
| **Refine Mobile Layout** | 🎨 Polishing | Medium |

---

## Verification Plan

### Automated Tests
Run the test suite to ensure no regressions in core agent logic:
```bash
python -m pytest tests/
```

### Manual Verification
1. **Launch**: `python start.py --dev`
2. **Connect**: Scan QR code with phone.
3. **Chat**: Send a message, verify it appears on desktop (CDP mode).
4. **Control**: Click "Stop" on mobile, verify desktop stops generating.
5. **Artifacts**: View a generated file on mobile.
