import asyncio
import aiohttp
import json

# Re-use the logic from cdp_client.py for consistent testing
SNAPSHOT_JS = """
(function() {
    function getReactFiber(node) {
        for (const key in node) {
            if (key.startsWith('__reactFiber$')) {
                return node[key];
            }
        }
        return null;
    }

    function findPropUpwards(fiber, propCheck, limit = 50) {
        let curr = fiber;
        let count = 0;
        while (curr && count < limit) {
            const props = curr.memoizedProps || {};
            if (propCheck(props)) {
                return props;
            }
            curr = curr.return;
            count++;
        }
        return null;
    }

    try {
        function findContainer(doc) {
            return doc.getElementById('conversation')
                || doc.getElementById('chat')
                || doc.getElementById('cascade')
                || doc.querySelector('.chat-list')
                || (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null);
        }

        let rootDoc = document;
        let container = findContainer(rootDoc);
        
        let iframeFound = false;
        if (!container) {
            const frames = document.querySelectorAll('iframe, webview');
            for (const frame of frames) {
                try {
                    const doc = frame.contentDocument;
                    if (doc) {
                        const found = findContainer(doc);
                        if (found) {
                            container = found;
                            iframeFound = true;
                            break;
                        }
                    }
                } catch(e) {}
            }
        }

        const debugInfo = {
            containerFound: !!container,
            containerId: container ? container.id : null,
            iframeUsed: iframeFound,
            fiberFound: false,
            trajectoryFound: false,
            error: null
        };

        if (!container) {
            debugInfo.error = 'chat_container_not_found';
            return debugInfo;
        }

        // --- Hunter-Seeker Logic ---
        let foundProps = null;
        const queue = [container];
        let checked = 0;
        const maxCheck = 500;

        while (queue.length > 0 && checked < maxCheck) {
            const node = queue.shift();
            checked++;

            const fiber = getReactFiber(node);
            if (fiber) {
                const props = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
                if (props) {
                    foundProps = props;
                    break;
                }
            }

            for (let i = 0; i < node.children.length; i++) {
                queue.push(node.children[i]);
            }
        }

        if (!foundProps) {
             debugInfo.error = 'trajectory_data_not_found_after_scan';
             debugInfo.nodesChecked = checked;
             return debugInfo;
        }
        
        debugInfo.trajectoryFound = true;
        debugInfo.nodesChecked = checked;
        debugInfo.stepCount = foundProps.trajectory.steps.length;
        
        return debugInfo;

    } catch (e) {
        return { error: e.toString() };
    }
})()
"""

async def run_diagnostic():
    try:
        # 1. Get CDP Connection
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:9222/json') as resp:
                targets = await resp.json()
                
        # Find the main window (usually Antigravity or similar)
        target = next((t for t in targets if 'Antigravity' in t.get('title', '') or t.get('type') == 'page'), targets[0])
        ws_url = target.get('webSocketDebuggerUrl')
        
        print(f"Connecting to: {target.get('title')} ({ws_url})")

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                
                # Helper to send/recv
                async def send(method, params={}):
                    cmd_id = getattr(send, 'id', 1)
                    setattr(send, 'id', cmd_id + 1)
                    await ws.send_json({'id': cmd_id, 'method': method, 'params': params})
                    return cmd_id

                # Await response
                async def wait_for(msg_id):
                    while True:
                        msg = await ws.receive_json()
                        if msg.get('id') == msg_id:
                            return msg

                # 1. Run SNAPSHOT_JS Diagnostic
                print("\n--- Running SNAPSHOT_JS Diagnostic ---")
                mid = await send('Runtime.evaluate', {
                    'expression': SNAPSHOT_JS,
                    'returnByValue': True,
                    'includeCommandLineAPI': True
                })
                res = await wait_for(mid)
                print(json.dumps(res, indent=2))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(run_diagnostic())
