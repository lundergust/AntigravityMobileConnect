
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

from server.cdp_client import discover_cdp, CDPConnection, SNAPSHOT_JS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    url = await discover_cdp(ports=[9222, 9000, 9001, 9002, 9003])
    if not url:
        print("CDP not found")
        return

    conn = CDPConnection(url)
    if not await conn.connect():
        print("Connect failed")
        return

    print("Running SNAPSHOT_JS...")
    # Run the ACTUAL logic we are using
    result = await conn.evaluate(SNAPSHOT_JS)
    
    if not result:
        print("No result returned")
    elif 'messages' not in result:
        print("No messages in result:", result.keys())
        if 'error' in result:
            print("Error:", result['error'])
    else:
        print(f"Total Messages Captured: {len(result['messages'])}")
        # Dump all IDs to see if ours are even there
        all_ids = [m['id'] for m in result['messages']]
        print("Captured IDs:", all_ids)
        
        # Look for step-0 and step-46 specifically
        for msg in result['messages']:
            if msg['id'] in ['step-0', 'step-46']:
                print(f"FOUND {msg['id']}:")
                print(json.dumps(msg, indent=2))
                
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
