import asyncio
import aiohttp
import json
import logging

# Re-use the JS from cdp_client.py EXACTLY
SNAPSHOT_JS = """
(function() {
    function findContainer(doc) {
        return doc.getElementById('conversation')
            || doc.getElementById('chat')
            || doc.getElementById('cascade')
            || doc.querySelector('.chat-list')
            || doc.querySelector('[aria-label="Chat"]');
    }

    try {
        let container = findContainer(document);
        
        // If not in main doc, check iframes
        if (!container) {
            const frames = document.querySelectorAll('iframe, webview');
            for (const frame of frames) {
                try {
                    const doc = frame.contentDocument;
                    if (doc) {
                        const found = findContainer(doc);
                        if (found) {
                            container = found;
                            break;
                        }
                    }
                } catch(e) {}
            }
        }

        if (!container) {
            return { error: 'chat_container_not_found', messages: [] };
        }

        // DUMP MODE: Verify role identification
        const messageList = container.querySelector('div[class*="gap-y-3"][class*="transition-[height]"]');
        
        const children = [];
        if (messageList) {
            for (const child of messageList.children) {
                 const firstChild = child.children[0];
                 children.push({
                    textPreview: child.innerText ? child.innerText.substring(0, 50).replace(/\\n/g, ' ') : '',
                    containerClass: child.className,
                    firstChildClass: firstChild ? firstChild.className : "NO_CHILD",
                    isUserCandidate: firstChild ? firstChild.className.includes("flex-row") : false,
                    isModelCandidate: firstChild ? firstChild.className.includes("flex-col") : false
                });
            }
        }

        return {
            mode: "role_verification",
            messages: children
        };






    } catch (e) {
        return { error: e.toString(), messages: [] };
    }
})()
"""

async def debug_extraction(port=9222):
    print(f"🔌 Connecting to CDP on port {port}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"http://localhost:{port}/json") as resp:
                targets = await resp.json()
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return

        # Prioritize 'workbench' but exclude 'Launchpad'
        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        
        # Find target that looks like the main workbench and is NOT Launchpad
        target = next(
            (t for t in pages if 
             "workbench.html" in t.get("url", "") and 
             "Launchpad" not in t.get("title", "")), 
            None
        )
        
        # Fallback to just anything not Launchpad
        if not target:
            target = next((t for t in pages if "Launchpad" not in t.get("title", "")), None)
            
        if not target:
            target = pages[0]

        
        if not target:
            print("❌ No valid target found.")
            return

        print(f"\n🔍 Target: {target.get('title')}")
        ws_url = target.get('webSocketDebuggerUrl')
            
        async with session.ws_connect(ws_url) as ws:
            print("🚀 Sending extraction JS...")
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
            
            print("\n📊 Extraction Result:")
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(debug_extraction())
