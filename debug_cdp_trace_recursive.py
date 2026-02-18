
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.append(str(Path.cwd()))
from server.cdp_client import discover_cdp, CDPConnection

logging.basicConfig(level=logging.INFO)

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

    function findAllContainers(doc, results = [], depth = 0) {
        if (depth > 10) return results; // Depth limit 10

        const candidates = [
            doc.getElementById('conversation'),
            doc.getElementById('chat'),
            doc.getElementById('cascade'),
            doc.querySelector('.chat-list'),
            (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null)
        ];
        
        candidates.forEach(c => {
            if (c) results.push({ element: c, depth: depth, url: doc.URL });
        });

        const frames = doc.querySelectorAll('iframe, webview');
        for (const frame of frames) {
            try {
                const innerDoc = frame.contentDocument;
                if (innerDoc) {
                    findAllContainers(innerDoc, results, depth + 1);
                }
            } catch(e) {}
        }
        return results;
    }

    const containers = findAllContainers(document);
    const log = [];
    
    for (const item of containers) {
        const container = item.element;
        let targetNode = container;
        const inner = container.querySelector('div[class*="gap-y-3"]');
        if (inner) targetNode = inner;

        let stepsFound = 0;
        let firstStepId = 'N/A';
        let foundType = 'none';

        // Strategy 1
        let fiber = getReactFiber(targetNode);
        let foundProps = null;
        if (fiber) {
             foundProps = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
             if (foundProps) foundType = 'self';
        }

        // Strategy 2
        if (!foundProps && targetNode.children.length > 0) {
             for (let i=0; i<Math.min(targetNode.children.length, 3); i++) {
                 fiber = getReactFiber(targetNode.children[i]);
                 if (fiber) {
                     foundProps = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
                     if (foundProps) {
                         foundType = `child-${i}`;
                         break;
                     }
                 }
             }
        }

        if (foundProps && foundProps.trajectory && foundProps.trajectory.steps) {
            stepsFound = foundProps.trajectory.steps.length;
            if (stepsFound > 0) {
                const s0 = foundProps.trajectory.steps[0];
                firstStepId = s0.id || (s0.step ? s0.step.id : 'no-id') || 'idx';
            }
        }

        log.push({
            id: container.id ? container.id : 'no-id',
            className: container.className ? container.className : 'no-class',
            depth: item.depth,
            url: item.url, 
            steps: stepsFound,
            firstIndex: firstStepId,
            foundType: foundType
        });
    }

    return log;
})()
"""

async def main():
    url = await discover_cdp(ports=[9222, 9000, 9001, 9002, 9003])
    conn = CDPConnection(url)
    await conn.connect()
    print("Tracing containers (recursive)...")
    result = await conn.evaluate(DEBUG_JS)
    print(json.dumps(result, indent=2))
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
