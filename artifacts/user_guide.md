# 📱 Antigravity Mobile Connect — User Guide

This guide helps you act as a "remote pilot" for your desktop Antigravity agent using your mobile phone.

## How It Works

Antigravity Mobile Connect create a "bridge" between your phone and your computer.
- **Your Computer**: Runs the heavy AI models and existing Antigravity agent.
- **Your Phone**: Acts as a lightweight remote control.
- **The Connection**: Uses a secure tunnel (ngrok) or your local Wi-Fi to link them.

---

## Features

### 1. CDP Mirroring (Default Mode)
**"See what your desktop sees."**

When you start the app, it automatically looks for a running Antigravity window on your desktop (via Chrome DevTools Protocol).
- **No Configuration**: You don't need to paste API keys into your phone.
- **Shared Session**: If you type on your phone, it appears on your desktop. If the desktop agent replies, it appears on your phone.
- **Remote Stopping**: If the agent goes off-track, hit the "Stop" button on your phone to halt generation immediately.

### 2. Headless Agent (Server Mode)
**"Run without a browser."**

If no desktop Antigravity window is found, the server starts its own invisible "Headless" agent.
- **Independent**: Useful if you want to run the agent on a server or background process.
- **Direct Control**: Your phone talks directly to the Python backend.

### 3. Connection Options

The startup script (`start.py`) offers three ways to connect:

| Method | Best For... | Command |
|--------|-------------|---------|
| **Local Network** | Home Wi-Fi. Fast, no internet needed. | `python start.py` |
| **Tailscale** | Secure remote access if you have Tailscale VPN installed. | `python start.py` (auto-detected) |
| **ngrok** | Remote access from anywhere (requires free ngrok account). | `python start.py --ngrok` |

---

## 🔧 Troubleshooting

### "I scan the QR code but it won't load"
1. **Check Network**: Your phone and computer must be on the **same Wi-Fi** for Local connection.
2. **Firewall**: Ensure Windows Firewall isn't blocking Python or port 8000.
3. **Try ngrok**: Run `python start.py --ngrok` to get a public URL that works over 4G/5G.

### "The chat isn't updating"
- **Refresh**: Pull down on the mobile page to refresh.
- **Check Desktop**: Is your desktop Antigravity agent running?
- **Reconnect**: Click the "Reconnect" button in the mobile app header.

### "How do I stop the server?"
- Press `Ctrl+C` in the terminal window where you ran `start.py`.

---

## ⌨️ Command Reference

| Command | Action |
|---------|--------|
| `/run` | Execute the pending code block. |
| `/reject` | Cancel the pending action. |
| `/clear` | Clear the chat history on the phone (does not affect desktop). |
