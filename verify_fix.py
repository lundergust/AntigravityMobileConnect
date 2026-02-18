import asyncio
import sys
import os
import logging
import json

# Configure logging

logging.basicConfig(level=logging.DEBUG)

# Add project root to path
sys.path.append(os.getcwd())


from server.cdp_client import discover_cdp, CDPConnection

async def verify():
    print("🔍 Discovering CDP target...")
    # NOTE: We can't easily get the title from here since discover_cdp only returns the WS URL
    # But we can assume it's the same logic.
    ws_url = await discover_cdp()
    if not ws_url:
        print("❌ Could not find Antigravity CDP target.")
        return


    print(f"✅ Found target: {ws_url}")
    
    conn = CDPConnection(ws_url)
    print("🔌 Connecting...")
    if await conn.connect():
        print("✅ Connected!")
        
        print("🧪 Testing simple evaluation...")
        res = await conn.evaluate("1 + 1")
        print(f"   Result: {res}")
        
        print("📸 Capturing snapshot (RAW)...")
        from server.cdp_client import SNAPSHOT_JS
        raw_res = await conn.evaluate(SNAPSHOT_JS)
        print(f"   Raw Result Type: {type(raw_res)}")
        print(f"   Raw Result: {json.dumps(raw_res, indent=2) if raw_res else 'None'}")


            
        await conn.disconnect()
    else:
        print("❌ Connection failed.")

if __name__ == "__main__":
    asyncio.run(verify())
