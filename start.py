"""
Antigravity Mobile Connect — Single-script launcher.

Starts the FastAPI bridge server, optionally launches ngrok/Tailscale tunnel,
and prints a QR code to the terminal for mobile access.

Usage:
    python start.py              # Production mode (serves built UI)
    python start.py --dev        # Dev mode (Vite dev server + API server)
    python start.py --ngrok      # Force ngrok tunnel
    python start.py --port 8000  # Custom port
"""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def get_local_ip() -> str:
    """Detect the machine's LAN IP address.

    Returns:
        The local IP address string.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_tailscale_ip() -> str | None:
    """Attempt to get the Tailscale IP.

    Returns:
        Tailscale IP string or None if unavailable.
    """
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def start_ngrok(port: int) -> str | None:
    """Start an ngrok tunnel and return the public URL.

    Args:
        port: The local port to tunnel.

    Returns:
        Public ngrok URL or None if unavailable.
    """
    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(port, "http")
        return tunnel.public_url
    except Exception as e:
        print(f"  ⚠️  ngrok failed: {e}")
        return None


def print_qr(url: str) -> None:
    """Print a QR code to the terminal.

    Args:
        url: The URL to encode in the QR code.
    """
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print(f"  (install qrcode[pil] for QR code display)")


def print_banner(urls: dict) -> None:
    """Print the startup banner with access URLs.

    Args:
        urls: Dict mapping source labels to URLs.
    """
    print()
    print("=" * 60)
    print("  🪐  ANTIGRAVITY MOBILE CONNECT")
    print("=" * 60)
    print()

    for label, url in urls.items():
        print(f"  {label}: {url}")

    print()

    # Print QR for the best available URL
    best_url = (
        urls.get("ngrok") or
        urls.get("tailscale") or
        urls.get("local")
    )
    if best_url:
        print(f"  📱 Scan this QR code to connect:")
        print()
        print_qr(best_url)
        print()
        print(f"  → {best_url}")

    print()
    print("=" * 60)
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()


def main() -> None:
    """Entry point for the launcher script."""
    parser = argparse.ArgumentParser(description="Antigravity Mobile Connect")
    parser.add_argument("--dev", action="store_true", help="Run in development mode")
    parser.add_argument("--ngrok", action="store_true", help="Force ngrok tunnel")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    args = parser.parse_args()

    port = args.port
    host = args.host

    # Collect access URLs
    urls: dict = {}

    # Local network
    local_ip = get_local_ip()
    urls["local"] = f"http://{local_ip}:{port}"

    # Tailscale
    ts_ip = get_tailscale_ip()
    if ts_ip:
        urls["tailscale"] = f"http://{ts_ip}:{port}"

    # ngrok
    if args.ngrok:
        print("  🔗 Starting ngrok tunnel...")
        ngrok_url = start_ngrok(port)
        if ngrok_url:
            urls["ngrok"] = ngrok_url

    # Start Vite dev server in dev mode
    vite_proc = None
    if args.dev:
        mobile_ui_dir = PROJECT_ROOT / "mobile-ui"
        if mobile_ui_dir.exists():
            print("  ⚡ Starting Vite dev server...")
            vite_proc = subprocess.Popen(
                ["npm", "run", "dev", "--", "--host"],
                cwd=str(mobile_ui_dir),
                shell=True,
            )
            urls["vite_dev"] = f"http://localhost:5173"

    print_banner(urls)

    # Handle graceful shutdown
    def shutdown(signum, frame):
        print("\n  🛑 Shutting down...")
        if vite_proc:
            vite_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start uvicorn
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host=host,
        port=port,
        reload=args.dev,
        log_level="info",
    )


if __name__ == "__main__":
    main()
