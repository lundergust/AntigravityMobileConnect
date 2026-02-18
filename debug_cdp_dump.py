
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

from server.cdp_client import discover_cdp, CDPConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("Finding CDP port...")
    url = await discover_cdp(ports=[9222, 9000, 9001, 9002, 9003])
    if not url:
        print("Could not find CDP endpoint.")
        return

    print(f"Connecting to {url}...")
    conn = CDPConnection(url)
    if not await conn.connect():
        print("Failed to connect.")
        return

    print("Capturing snapshot...")
    snapshot = await conn.capture_snapshot()
    
    if snapshot:
        # print(json.dumps(snapshot, indent=2))
        
        print(f"\nTotal Messages: {len(snapshot.get('messages', []))}")
        print("-" * 40)
        
        for i, msg in enumerate(snapshot.get('messages', [])):
            content = msg.get('content', '')
            preview = content[:100].replace('\n', '\\n')
            print(f"[{i}] Role: {msg.get('role')} | ID: {msg.get('id')} | Type: {msg.get('type')}")
            print(f"    Content Start: {preview}...")
            if "<EPHEMERAL_MESSAGE>" in content:
                print("    [!] CONTAINS EPHEMERAL_MESSAGE")
            if "Conversation History" in content:
                print("    [!] CONTAINS CONVERSATION HISTORY")
            print("-" * 40)
            
    else:
        print("No snapshot returned.")

    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
