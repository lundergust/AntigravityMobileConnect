
import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.cdp_client import discover_cdp, CDPConnection

DEBUG_FIBER_JS = """
(function() {
    function findContainer(doc) {
        return doc.getElementById('conversation')
            || doc.getElementById('chat')
            || doc.getElementById('cascade')
            || doc.querySelector('.chat-list')
            || doc.querySelector('[aria-label="Chat"]');
    }

    // Generic React Fiber finder
    function getReactFiber(node) {
        for (const key in node) {
            if (key.startsWith('__reactFiber$')) {
                return node[key];
            }
        }
        return null;
    }

    // Walk up until we find interesting data
    function findDataComponent(fiber, limit = 20) {
        let curr = fiber;
        let count = 0;
        while (curr && count < limit) {
            const props = curr.memoizedProps || {};
            
            if (props.queuedSteps || props.trajectory) { // || props.messages || props.turns) {
                const debugData = {
                    found: true,
                    type: curr.type ? (curr.type.name || curr.type.displayName || (typeof curr.type === 'string' ? curr.type : 'Component')) : 'unknown',
                    propKeys: Object.keys(props),
                    trajectoryType: Array.isArray(props.trajectory) ? 'array' : typeof props.trajectory,
                };
                
                if (props.trajectory && typeof props.trajectory === 'object') {
                    // Check steps
                    if (props.trajectory.steps && Array.isArray(props.trajectory.steps)) {
                        debugData.stepCount = props.trajectory.steps.length;
                        if (props.trajectory.steps.length > 0) {
                             const step = props.trajectory.steps[props.trajectory.steps.length - 1]; // Get last step, might be more interesting
                             debugData.lastStepKeys = Object.keys(step);
                             // Dump some values to guess structure
                             debugData.lastStepPreview = {
                                 id: step.id,
                                 type: step.type,
                                 keys: Object.keys(step),
                                 contentStart: step.content ? (typeof step.content === 'string' ? step.content.substring(0, 50) : 'OBJ:' + Object.keys(step.content)) : 'n/a'
                             };
                        }
                    }
                }

                if (Array.isArray(props.trajectory) && props.trajectory.length > 0) {
                     // ... (keep existing array logic if it was an array)
                     debugData.trajectorySample = props.trajectory.slice(0, 2);
                }
                
                return debugData;
            }
            curr = curr.return;
            count++;
        }
        return null;
    }

    // ... (rest of code)
    
    // Helper helper
    function getReactFiber(node) {
        for (const key in node) {
            if (key.startsWith('__reactFiber$')) {
                return node[key];
            }
        }
        return null;
    }
    
    function findContainer(doc) {
        // ... (same as before)
        return doc.getElementById('conversation')
            || doc.getElementById('chat')
            || doc.getElementById('cascade')
            || doc.querySelector('.chat-list')
            || (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null);
    }


    // ... (keep helper functions)

    try {
        const frames = document.querySelectorAll('iframe, webview');
        // ... (iframe finding logic)
        let doc = null;
        if (frames.length > 0) {
             try { doc = frames[0].contentDocument; } catch(e){}
             if (!doc) {
                 for (const f of frames) {
                     if (f.src.includes('cascade')) {
                         try { doc = f.contentDocument; } catch(e){}
                         break;
                     }
                 }
             }
        }
        if (!doc) return { error: "frame_document_null" };

        const root = findContainer(doc);
        if (!root) return { error: "container_not_found_in_frame" };

        const container = root.querySelector('div[class*="gap-y-3"][class*="transition-[height]"]');
        if (!container) return { error: "list_container_not_found" };

        // Iterate children like before
        for (let i = 0; i < Math.min(container.children.length, 3); i++) {
            const el = container.children[i];
            const fiber = getReactFiber(el);
            const data = findDataComponent(fiber);
            
            if (data && data.found) {
                return {
                    source: 'child_' + i,
                    foundData: true,
                    data: data
                };
            }
        }

        return { foundData: false, error: "data_component_not_found_in_children" };

    } catch(e) {
        return { error: e.toString() };
    }
})()
"""

async def debug_fiber():
    print("🔍 Connecting to CDP...")
    ws_url = await discover_cdp()
    if not ws_url:
        print("❌ Could not find Antigravity instance.")
        return

    conn = CDPConnection(ws_url)
    if await conn.connect():
        print("✅ Connected!")
        print("🔍 Injecting Fiber Debug Script...")
        result = await conn.evaluate(DEBUG_FIBER_JS)
        print("\n--- Fiber Debug Result ---")
        import json
        print(json.dumps(result, indent=2))
        await conn.disconnect()
    else:
        print("❌ Connection failed.")

if __name__ == "__main__":
    asyncio.run(debug_fiber())
