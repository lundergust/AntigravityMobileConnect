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
-   **CDP Mirroring**: Automatically mirror your desktop session (no API key required).
-   **Review History**: Browse and manage past conversations.
-   **Monitor Usage**: Keep track of token usage and quotas (Coming Soon).

It consists of a **FastAPI bridge server** and a **React/Vite frontend**, connected via secure tunnels (ngrok or Tailscale) or local Wi-Fi.

---

## 🏗️ Architecture & Documentation

For deep dives into how this works, see the new documentation artifacts:

-   **[Architecture Overview](artifacts/architecture.md)** — System design, components, and data flow.
-   **[Implementation Plan](artifacts/antigravity_mobile_connect_implementation_plan.md)** — Detailed roadmap and change log.

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
# Standard Launch (Local + Tailscale + CDP Mirror)
python start.py

# Launch with ngrok public tunnel (recommended for remote access)
python start.py --ngrok

# Developer Mode (Hot Module Replacement + API Server)
python start.py --dev
```

### 4. Connect

Scan the **QR code** printed in your terminal with your phone. No app installation required—it works directly in your mobile browser.

---

## ✨ Features

| Feature | Description | Status |
| :--- | :--- | :--- |
| **💬 Real-time Chat** | Low-latency WebSocket connection to your agent. | ✅ Live |
| **🖥️ CDP Mirroring** | **Mirrors your desktop Antigravity session** (via Chrome DevTools Protocol) without requiring an API key. | ✅ Live |
| **📜 History** | Auto-saves conversations. Browse past chats. | 🚧 In Progress |
| **🤖 Agent Discovery** | Auto-detects available agents in your workspace. | 🚧 In Progress |
| **🚀 Swarm Control** | Deploy agent swarms for complex tasks. | 📅 Planned |
| **🔌 Auto-Connect** | Smart detection of Local LAN, Tailscale, and ngrok tunnels. | ✅ Live |

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

## 🤝 Contributing

Contributions are welcome! Please check out the `docs/` folder for architectural details or open an issue.

**License**: MIT
