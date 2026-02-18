
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
        // Check current doc
        const candidates = [
            doc.getElementById('conversation'),
            doc.getElementById('chat'),
            doc.getElementById('cascade'),
            doc.querySelector('.chat-list'),
            (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null)
        ];
        
        candidates.forEach(c => {
            if (c) results.push({ type: 'direct', node: c, docUrl: doc.location ? doc.location.href : 'unknown' });
        });

        // Check iframes
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
    
    if (containers.length === 0) return { error: "No containers found" };

    const debugResults = [];

    for (const containerObj of containers) {
        const container = containerObj.node;
        
        // Find props
        let targetNode = container;
        const inner = container.querySelector('div[class*="gap-y-3"]');
        if (inner) targetNode = inner;

        let foundProps = null;
        let fiber = getReactFiber(targetNode);
        if (fiber) foundProps = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
        
        if (!foundProps && targetNode.children.length > 0) {
             // Try children
             for (let i=0; i<Math.min(targetNode.children.length, 3); i++) {
                 fiber = getReactFiber(targetNode.children[i]);
                 if (fiber) {
                     foundProps = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
                     if (foundProps) break;
                 }
             }
        }

        if (foundProps) {
            const steps = foundProps.trajectory.steps;
            debugResults.push({
                found: true,
                docUrl: containerObj.docUrl,
                totalSteps: steps.length,
                sample: steps.slice(0, 10).map((item, index) => {
                    let step = item.step || item;
                    if (step.value) step = step.value;
                    
                    return {
                        id: step.id || item.id,
                        type: step.type,
                        keys: Object.keys(step),
                        contentPreview: step.content ? (typeof step.content === 'string' ? step.content.substring(0, 50) : 'OBJ') : 'NULL'
                    };
                })
            });
        } else {
            debugResults.push({ found: false, docUrl: containerObj.docUrl, reason: "No trajectory props" });
        }
    }

    return { results: debugResults };
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

    print("Running debug JS...")
    result = await conn.evaluate(DEBUG_JS)
    print(json.dumps(result, indent=2))
    
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
