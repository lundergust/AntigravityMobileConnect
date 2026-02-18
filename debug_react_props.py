import asyncio
import os
import json
import logging
from server.cdp_client import CDPConnection, discover_cdp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JS to inspect React props
REACT_PROPS_JS = """
(function() {
    function findContainer(doc) {
        return doc.getElementById('conversation')
            || doc.getElementById('chat')
            || doc.querySelector('.chat-list')
            || doc.querySelector('[aria-label="Chat"]');
    }

    let root = findContainer(document);
    if (!root) return { error: 'Root not found' };

    const container = root.querySelector('div[class*="gap-y-3"][class*="transition-[height]"]');
    if (!container) return { error: 'Container not found' };

    const results = [];
    
    for (const child of container.children) {
        if (child.className.includes('absolute')) continue;
        
        // Find React key/props
        let reactKey = null;
        let internalKey = Object.keys(child).find(k => k.startsWith('__reactFiber$'));
        if (internalKey) {
            reactKey = child[internalKey].key;
        }

        results.push({
            tagName: child.tagName,
            className: child.className,
            innerText: (child.innerText || '').substring(0, 50),
            reactKey: reactKey,
            dataTurnId: child.getAttribute('data-turn-id')
        });
    }

    return results;
})()
"""

async def run_debug():
    print("🔍 Discovering CDP target...")
    target = await discover_cdp()
    if not target:
        print("❌ No target found.")
        return

    conn = CDPConnection(target['webSocketDebuggerUrl'])
    if await conn.connect():
        print("✅ Connected!")
        print("🔍 Inspecting React props...")
        result = await conn.evaluate(REACT_PROPS_JS)
        print(json.dumps(result, indent=2))
        await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(run_debug())
