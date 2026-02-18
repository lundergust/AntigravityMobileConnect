import asyncio
import aiohttp
import json

SNAPSHOT_JS = """
(function() {
    // 1. Check main document
    const container = document.getElementById('conversation')
        || document.getElementById('chat')
        || document.getElementById('cascade')
        || document.querySelector('.chat-list')
        || document.querySelector('[aria-label="Chat"]');

    if (container) return { found: true, details: 'Main document', id: container.id };

    // 2. Check iframes
    const frames = document.querySelectorAll('iframe');
    const frameResults = [];
    for (let i = 0; i < frames.length; i++) {
        try {
            const frameDoc = frames[i].contentDocument;
            if (frameDoc) {
                const found = frameDoc.getElementById('conversation')
                    || frameDoc.getElementById('chat')
                    || frameDoc.getElementById('cascade');
                if (found) {
                    frameResults.push({ index: i, id: found.id, src: frames[i].src });
                }
            }
        } catch(e) {
            frameResults.push({ index: i, error: e.toString() }); 
        }
    }
    
    return { 
        found: frameResults.length > 0, 
        frames: frameResults, 
        info: document.title,
        url: window.location.href
    };
})()
"""

async def debug_cdp(port=9222):
    print(f"🔌 Connecting to CDP on port {port}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"http://localhost:{port}/json") as resp:
                targets = await resp.json()
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return

        print(f"📄 Found {len(targets)} targets. Scanning all page targets...")
        
        for t in targets:
            if t.get('type') != 'page':
                continue
                
            title = t.get('title')
            url = t.get('url')
            ws_url = t.get('webSocketDebuggerUrl')
            
            if not ws_url:
                continue
                
            print(f"\n🔍 Scanning Target: {title}")
            print(f"   URL: {url}")
            
            try:
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_json({
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": SNAPSHOT_JS,
                            "returnByValue": True
                        }
                    })
                    
                    resp = await ws.receive_json()
                    result = resp.get('result', {}).get('result', {}).get('value')
                    print(f"   Result: {json.dumps(result)}")
            except Exception as e:
                print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_cdp())
