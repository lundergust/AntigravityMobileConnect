import asyncio
import aiohttp
import json

async def verify_websocket():
    url = "ws://localhost:8000/ws"
    print(f"🔌 Connecting to {url}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as ws:
                print("✅ Connected! Waiting for messages...")
                
                # Wait for initial state or update
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=10.0)
                    
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        print(f"📩 Received message type: {data.get('type')}")
                        if data.get('type') == 'snapshot_update':
                            count = data.get('count', 0)
                            print(f"✅ SUCCESS: Received snapshot update with {count} messages.")
                            print("Sample message:", json.dumps(data.get('messages', [])[:1], indent=2))
                        else:
                            print(f"⚠️ Received unknown message: {data}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print('❌ WebSocket connection closed with exception %s', ws.exception())
                except asyncio.TimeoutError:
                    print("❌ TIMEOUT: No message received after 10 seconds.")
                    
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_websocket())
