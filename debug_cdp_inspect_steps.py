
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path.cwd()))

from server.cdp_client import discover_cdp, CDPConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEBUG_JS = """
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

    // Recursive finder
    function findAllContainers(doc, results = []) {
        const candidates = [
            doc.getElementById('conversation'),
            doc.getElementById('chat'),
            doc.getElementById('cascade'),
            doc.querySelector('.chat-list'),
            (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null)
        ];
        
        candidates.forEach(c => {
            if (c) results.push(c);
        });

        const frames = doc.querySelectorAll('iframe, webview');
        for (const frame of frames) {
            try {
                const innerDoc = frame.contentDocument;
                if (innerDoc) {
                    findAllContainers(innerDoc, results);
                }
            } catch(e) {}
        }
        return results;
    }

    const containers = findAllContainers(document);
    if (containers.length === 0) return { error: "No containers" };
    
    // Find props
    let foundProps = null;
    for (const container of containers) {
        let targetNode = container;
        const inner = container.querySelector('div[class*="gap-y-3"]');
        if (inner) targetNode = inner;

        let fiber = getReactFiber(targetNode);
        if (fiber) foundProps = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
        
        if (!foundProps && targetNode.children.length > 0) {
             for (let i=0; i<Math.min(targetNode.children.length, 3); i++) {
                 fiber = getReactFiber(targetNode.children[i]);
                 if (fiber) {
                     foundProps = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
                     if (foundProps) break;
                 }
             }
        }
        if (foundProps) break;
    }

    if (!foundProps) return { error: "Props not found" };

    const steps = foundProps.trajectory.steps;
    
    // Indices to inspect: 0-2 (Start), and around 40-50 (Notify User)
    // Adjust based on typical length, maybe just dump relevant ones
    
    const relevantIndices = [0, 1, 2, 40, 41, 42, 43, 44, 45, 46, 47];
    
    return {
        selectedSteps: steps
            .map((item, index) => ({ item, index }))
            .filter(x => relevantIndices.includes(x.index))
            .map(x => {
                let step = x.item.step || x.item;
                if (step.value) step = step.value;
                
                // Sanitized dump
                return {
                    index: x.index,
                    keys: Object.keys(step),
                    userResponse: step.userResponse,
                    query: step.query,
                    toolCalls: step.toolCalls,
                    type: step.type,
                    // If toolCalls exists, try to show it
                    toolCallsPreview: step.toolCalls ? JSON.stringify(step.toolCalls) : null
                };
            })
    };
})()
"""

async def main():
    url = await discover_cdp(ports=[9222, 9000, 9001, 9002, 9003])
    if not url:
        print("CDP not found")
        return

    conn = CDPConnection(url)
    if not await conn.connect():
        print("Connect failed")
        return

    print("Running debug inspection...")
    result = await conn.evaluate(DEBUG_JS)
    print(json.dumps(result, indent=2))
    
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
