# 🪐 Antigravity Mobile Connect

> Mobile-first web client for remote control of the Antigravity agent manager.

## Executive Summary

Antigravity Mobile Connect is a companion interface that gives you full control over your Antigravity agent manager from your phone. A FastAPI bridge server runs alongside the Antigravity core on your PC, serving a React SPA designed for mobile browsers. Access is provided via QR code over ngrok or Tailscale.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ & npm
- An Antigravity workspace with a `.env` file configured

### 1. Install Dependencies

```bash
cd c:\Users\Joe\Documents\AntigravityMobileConnect

# Python server dependencies
pip install -r requirements.txt

# Mobile UI dependencies
cd mobile-ui && npm install && cd ..
```

### 2. Build the Mobile UI

```bash
cd mobile-ui && npm run build && cd ..
```

### 3. Launch

```bash
# Production mode — serves built UI, prints QR code
python start.py

# Development mode — Vite HMR + API server
python start.py --dev

# With ngrok tunnel for remote access
python start.py --ngrok
```

### 4. Connect Your Phone

Scan the QR code printed in your terminal. The app opens in your mobile browser — no install required.

---

## Features (Phase 0)

| Feature | Status | Description |
|---------|--------|-------------|
| **Chat** | ✅ | Send messages, receive agent responses, auto-save history |
| **Chat History** | ✅ | Browse, search, reopen, and delete old conversations |
| **New Chat** | ✅ | Auto-saves current chat before clearing |
| **Agents** | ✅ | Discover agents in `src/agents/`, deploy individually or as swarm |
| **Quota Dashboard** | ✅ | Cockpit-style gauges (mock data — real API in Phase 5) |
| **Settings** | ✅ | Workspace & model selection |
| **Connectivity** | ✅ | Auto-detects ngrok/Tailscale, QR code in terminal |
| **WebSocket** | ✅ | Real-time connection with auto-reconnect |

---

## Project Structure

```
AntigravityMobileConnect/
├── start.py                    # Single-script launcher
├── requirements.txt            # Python dependencies
├── server/                     # FastAPI bridge server
│   ├── app.py                  # Application factory
│   ├── ws_hub.py               # WebSocket connection manager
│   ├── bridge.py               # Wraps src/ core for REST/WS
│   └── routes/
│       ├── chat.py             # Chat messaging endpoints
│       ├── workspace.py        # Workspace & model selection
│       ├── agents.py           # Agent discovery & deployment
│       ├── quota.py            # Quota monitoring (mock)
│       └── history.py          # Chat history CRUD
├── mobile-ui/                  # Vite + React + TypeScript
│   ├── vite.config.ts          # Dev proxy to FastAPI
│   ├── src/
│   │   ├── App.tsx             # Shell: top nav, routing, bottom nav
│   │   ├── index.css           # Dark design system
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts # Auto-reconnecting WebSocket
│   │   │   └── useApi.ts       # REST API wrapper
│   │   └── pages/
│   │       ├── ChatPage.tsx    # Chat with auto-save
│   │       ├── HistoryPage.tsx # Conversation browser
│   │       ├── AgentsPage.tsx  # Agent grid + swarm deploy
│   │       ├── QuotaPage.tsx   # Cockpit-style dashboard
│   │       └── SettingsPage.tsx # Workspace/model config
│   └── dist/                   # Built production bundle
└── docs/
    └── en/mobile-connect/      # This documentation
```

---

## API Reference

All endpoints are prefixed with `/api`.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Server status, connected clients, version |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/send` | Send a message to the agent |
| `GET` | `/api/chat/history` | Get current session messages |
| `POST` | `/api/chat/action` | Execute Run/Reject commands |

### History

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/history/` | List all saved conversations |
| `GET` | `/api/history/{id}` | Load a specific conversation |
| `POST` | `/api/history/save` | Save conversation (accepts `messages[]` and `title`) |
| `DELETE` | `/api/history/{id}` | Delete a conversation |

### Workspace & Model

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/workspaces` | List available workspaces |
| `POST` | `/api/workspace/select` | Switch active workspace |
| `GET` | `/api/models` | List available AI models |
| `POST` | `/api/model/select` | Switch active model |

### Agents

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/agents/` | Auto-discover agents in `src/agents/` |
| `POST` | `/api/agents/{id}/deploy` | Deploy a single agent |
| `POST` | `/api/agents/swarm/deploy` | Launch agent swarm with a task |

### Quota

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/quota/` | Get quota usage per model |
| `GET` | `/api/quota/settings` | Get warning/danger thresholds |

### WebSocket

| Protocol | Path | Description |
|----------|------|-------------|
| `WS` | `/ws` | Real-time bidirectional communication |

---

## Configuration

### Environment Variables

The server reads from the existing `.env` file:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Gemini API authentication |
| `GEMINI_MODEL_NAME` | Default model for the agent |

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8000` | Server port |
| `--dev` | `false` | Enable Vite dev server with HMR |
| `--ngrok` | `false` | Force ngrok tunnel |
| `--host` | `0.0.0.0` | Bind address |

---

## Roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **0** | Foundation — server, UI shell, connectivity | ✅ Complete |
| **1** | Real agent chat with streaming responses | 🔜 Next |
| **2** | Workspace & model selection (live) | 📋 Planned |
| **3** | Chat history (advanced features) | 📋 Planned |
| **4** | Agent discovery & deployment (live) | 📋 Planned |
| **5** | Quota dashboard (real API) | 📋 Planned |
| **6** | Polish, PWA, documentation | 📋 Planned |
