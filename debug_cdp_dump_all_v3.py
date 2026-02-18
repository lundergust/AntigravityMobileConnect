
import asyncio
import json
import logging
import sys
import re
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

from server.cdp_client import discover_cdp, CDPConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_snapshot_js():
    # Read the file directly to get the variable content
    try:
        with open('server/cdp_client.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract SNAPSHOT_JS = """ ... """ block
        match = re.search(r'SNAPSHOT_JS\s*=\s*"""(.*?)"""', content, re.DOTALL)
        if match:
            return match.group(1)
        else:
            print("Could not find SNAPSHOT_JS in cdp_client.py")
            return None
    except Exception as e:
        print(f"Error reading cdp_client.py: {e}")
        return None

async def main():
    js_code = get_snapshot_js()
    if not js_code:
        return

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

    print("Running SNAPSHOT_JS from file...")
    try:
        # Run safely with timeout
        result = await asyncio.wait_for(conn.evaluate(js_code), timeout=15.0)
        
        if not result:
            print("No result returned (None)")
        elif 'messages' not in result:
            print("No messages in result:", result.keys())
            if 'error' in result:
                print("Error from JS:", result['error'])
        else:
            print(f"Total Messages Captured: {len(result['messages'])}")
            
            # Print ALL messages briefly
            ids_found = []
            for msg in result['messages']:
                ids_found.append(msg.get('id'))
                content_preview = msg.get('content', '')[:50].replace('\n', ' ')
                print(f"ID: {msg.get('id')} | Role: {msg.get('role')} | Type: {msg.get('type')} | Content: {content_preview}...")

            if 'step-0' not in ids_found:
                 print("\nWARNING: step-0 NOT FOUND in captured messages.")
            else:
                 print("\nSUCCESS: step-0 FOUND.")
                 
            if 'step-46' not in ids_found:
                 print("\nWARNING: step-46 NOT FOUND in captured messages.")
            else:
                 print("\nSUCCESS: step-46 FOUND.")

    except asyncio.TimeoutError:
        print("Timeout executing JS!")
    except Exception as e:
        print(f"Exception: {e}")
                
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
