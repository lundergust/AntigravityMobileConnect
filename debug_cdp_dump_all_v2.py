
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

try:
    from server.cdp_client import discover_cdp, CDPConnection, SNAPSHOT_JS
except ImportError:
    # If SNAPSHOT_JS isn't exported in __init__ (it's not), read it from file
    from server.cdp_client import discover_cdp, CDPConnection
    # We'll just define a fallback or read it from the file manually if needed, 
    # but likely it's available if we imported from the module. Unfortunately it's a variable in the module.
    import server.cdp_client
    SNAPSHOT_JS = server.cdp_client.SNAPSHOT_JS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("Discovering CDP...")
    url = await discover_cdp(ports=[9222, 9000, 9001, 9002, 9003])
    if not url:
        print("CDP not found")
        return

    print(f"Connecting to {url}...")
    conn = CDPConnection(url)
    if not await conn.connect():
        print("Connect failed")
        return

    print("Running SNAPSHOT_JS...")
    try:
        # Run safely with timeout
        result = await asyncio.wait_for(conn.evaluate(SNAPSHOT_JS), timeout=10.0)
        
        if not result:
            print("No result returned (None)")
        elif 'messages' not in result:
            print("No messages in result:", result.keys())
            if 'error' in result:
                print("Error from JS:", result['error'])
        else:
            print(f"Total Messages Captured: {len(result['messages'])}")
            
            # Print ALL messages briefly
            for msg in result['messages']:
                content_preview = msg.get('content', '')[:50].replace('\n', ' ')
                print(f"ID: {msg.get('id')} | Role: {msg.get('role')} | Type: {msg.get('type')} | Content: {content_preview}...")

    except asyncio.TimeoutError:
        print("Timeout executing JS!")
    except Exception as e:
        print(f"Exception: {e}")
                
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
