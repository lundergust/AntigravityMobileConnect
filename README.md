# 🪐 Antigravity Mobile Connect

> **Mobile-first command center for your Antigravity Agent.**
> Control your agent, manage tasks, and monitor quotas from anywhere via a secure mobile web interface.

![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Beta-orange)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React%20%2B%20Vite-blue)
![Powered By](https://img.shields.io/badge/Powered%20By-Antigravity%20Template-purple)

## 📱 What is this?

**Antigravity Mobile Connect** is a companion app that runs alongside your Antigravity Agent on your desktop. It bridges the gap between your powerful desktop agent and your mobile device, allowing you to:

-   **Chat & Command**: Talk to your agent via a mobile-optimized interface.
-   **Deploy Swarms**: Launch complex multi-agent tasks on the go.
-   **Monitor Usage**: Keep track of token usage and quotas with cockpit-style gauges.
-   **Review History**: Browse and manage past conversations.

It consists of a **FastAPI bridge server** and a **React/Vite frontend**, connected via secure tunnels (ngrok or Tailscale) or local Wi-Fi.

---

## 🏗️ Architecture & Origins

This project is built on top of the **[Antigravity Workspace Template](https://github.com/study8677/antigravity-workspace-template)**.

While **Mobile Connect** provides the frontend interface, the **backend agent** retains all the powerful capabilities of the original template:

| Feature | Description |
| :--- | :--- |
| 🧠 **Infinite Memory** | Recursive summarization compresses context automatically. |
| 🛠️ **Universal Tools** | Drop Python functions in `src/tools/` → auto-discovered. |
| 🔌 **MCP Support** | Connect to GitHub, databases, and custom servers via Model Context Protocol. |
| 🤖 **Swarm Agents** | Multi-agent orchestration with Router-Worker pattern. |
| 📚 **Auto Context** | Add files to `.context/` → auto-injected into prompts. |

For deep dives into the agent architecture, see the core documentation:
-   **[Philosophy](docs/en/PHILOSOPHY.md)** — Core concepts & architecture
-   **[MCP Integration](docs/en/MCP_INTEGRATION.md)** — External tool connectivity
-   **[Swarm Protocol](docs/en/SWARM_PROTOCOL.md)** — Multi-agent coordination

---

## ⚡ Quick Start

### Prerequisites

-   **Python 3.11+**
-   **Node.js 18+**
-   An existing **Antigravity Workspace** (with `.env` configured).

### 1. Installation

Install backend and frontend dependencies:

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd mobile-ui
npm install
cd ..
```

### 2. Build

Build the mobile UI for production:

```bash
cd mobile-ui
npm run build
cd ..
```

### 3. Launch

Start the bridge server. This will serve the built UI and provide a QR code for easy connection.

```bash
# Standard Launch (Local + Tailscale auto-detect)
python start.py

# Launch with ngrok tunnel (recommended for remote access)
python start.py --ngrok

# Developer Mode (Hot Module Replacement + API Server)
python start.py --dev
```

### 4. Connect

Scan the **QR code** printed in your terminal with your phone. No app installation required—it works directly in your mobile browser.

---

## ✨ Features

| Feature | Description |
| :--- | :--- |
| **💬 Real-time Chat** | Low-latency WebSocket connection to your agent. |
| **📜 History** | Auto-saves conversations. Browse, search, and delete old chats. |
| **🤖 Agent Discovery** | Auto-detects available agents in your workspace. |
| **🚀 Swarm Control** | Deploy agent swarms for complex tasks directly from the UI. |
| **📊 Quota Cockpit** | Visual dashboard for model limits and token usage (Coming Soon). |
| **🔌 Auto-Connectivity** | Smart detection of Local LAN, Tailscale, and ngrok tunnels. |

---

## 🛠️ Configuration

Configuration is handled via command-line arguments and your existing `.env` file.

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--port` | Server port | `8000` |
| `--host` | Bind address | `0.0.0.0` |
| `--dev` | Enable Vite dev server proxy | `False` |
| `--ngrok` | Force remote tunnel creation | `False` |

---

## 🗺️ Roadmap

-   [x] **Phase 0**: Core Connectivity & UI Shell
-   [ ] **Phase 1**: Real-time Streaming Responses
-   [ ] **Phase 2**: Live Workspace & Model Switching
-   [ ] **Phase 3**: Advanced Chat History Management
-   [ ] **Phase 4**: Agent Deployment UI
-   [ ] **Phase 5**: Real Metrics Integration

---

## 🤝 Contributing

Contributions are welcome! Please check out the `docs/` folder for architectural details or open an issue.

**License**: MIT
