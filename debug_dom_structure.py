import asyncio
import os
import json
import logging
from server.cdp_client import CDPConnection, discover_cdp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JS to dump structure with attributes to find stable IDs and Artifact classes
DUMP_JS = """
(function() {
    function findContainer(doc) {
        return doc.getElementById('conversation')
            || doc.getElementById('chat')
            || doc.getElementById('cascade')
            || doc.querySelector('.chat-list')
            || doc.querySelector('[aria-label="Chat"]');
    }

    let root = findContainer(document);
    if (!root) {
        const frames = document.querySelectorAll('iframe, webview');
        for (const frame of frames) {
            try {
                const doc = frame.contentDocument;
                if (doc) {
                    const found = findContainer(doc);
                    if (found) {
                        root = found;
                        break;
                    }
                }
            } catch(e) {}
        }
    }

    if (!root) return { error: 'Root not found' };

    const container = root.querySelector('div[class*="gap-y-3"][class*="transition-[height]"]');
    if (!container) return { error: 'Container not found', rootHtml: root.outerHTML.substring(0, 500) };

    const messages = [];
    let index = 0;
    
    for (const child of container.children) {
        // Skip status
        if (child.className.includes('absolute') && child.className.includes('bottom')) continue;
        
        const firstChild = child.children[0];
        const firstChildClass = firstChild ? firstChild.className : '';
        
        // Deep dump of attributes and structure
        const msgData = {
            index: index++,
            tagName: child.tagName,
            className: child.className,
            id: child.id,
            attributes: {},
            firstChildClass: firstChildClass,
            innerText: (child.innerText || '').substring(0, 100),
            htmlSample: child.outerHTML.substring(0, 300)
        };
        
        // Collect all attributes
        for (const attr of child.attributes) {
            msgData.attributes[attr.name] = attr.value;
        }

        messages.push(msgData);
    }

    return {
        messageCount: messages.length,
        scrollHeight: container.scrollHeight,
        clientHeight: container.clientHeight,
        scrollTop: container.scrollTop,
        messages: messages
    };
})()
"""

async def run_debug():
    print("🔍 Discovering CDP target...")
    target = await discover_cdp()
    
    if not target:
        print("❌ No suitable CDP target found. Make sure Antigravity is running.")
        return

    print(f"✅ Found target: {target['webSocketDebuggerUrl']}")
    
    conn = CDPConnection(target['webSocketDebuggerUrl'])
    if await conn.connect():
        print("✅ Connected!")
        print("🔍 Analyzing DOM...")
        
        result = await conn.evaluate(DUMP_JS)
        
        if result:
            print(json.dumps(result, indent=2))
            
            # Save to file for easy reading
            with open('dom_dump.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            print("💾 Dump saved to dom_dump.json")
        else:
            print("❌ Evaluation returned None")
            
        await conn.disconnect()
    else:
        print("❌ Failed to connect.")

if __name__ == "__main__":
    asyncio.run(run_debug())
