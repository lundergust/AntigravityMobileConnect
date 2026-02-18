
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
        // Try with deeper limit 10 to see if 5 was too shallow/conservative
        if (depth > 10) return results;

        const candidates = [
            doc.getElementById('conversation'),
            doc.getElementById('chat'),
            doc.getElementById('cascade'),
            doc.querySelector('.chat-list'),
            (doc.getElementById('react-app') ? doc.getElementById('react-app').querySelector('div[class*="gap-y"]') : null)
        ];
        
        candidates.forEach(c => {
            if (c) results.push({ element: c, depth: depth, docUrl: doc.URL });
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

    const found = findAllContainers(document);
    
    return found.map(f => {
        const container = f.element;
        let targetNode = container;
        const inner = container.querySelector('div[class*="gap-y-3"]');
        if (inner) targetNode = inner;

        let traj = null;
        let source = 'none';

        let fiber = getReactFiber(targetNode);
        if (fiber) {
            const props = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
            if (props) {
                traj = props.trajectory;
                source = 'self';
            }
        }

        if (!traj && targetNode.children.length > 0) {
             for (let i=0; i<Math.min(targetNode.children.length, 3); i++) {
                 fiber = getReactFiber(targetNode.children[i]);
                 if (fiber) {
                     const props = findPropUpwards(fiber, (p) => p.trajectory && p.trajectory.steps);
                     if (props) {
                         traj = props.trajectory;
                         source = `child-${i}`;
                         break;
                     }
                 }
             }
        }

        return {
            id: container.id,
            className: container.className,
            depth: f.depth,
            docUrl: f.docUrl,
            hasTrajectory: !!traj,
            stepCount: traj ? traj.steps.length : 0,
            firstIndex: (traj && traj.steps.length > 0) ? (traj.steps[0].id || traj.steps[0].step?.id || 'idx-'+traj.steps[0].index) : 'N/A',
            source: source
        };
    });
})()
"""

async def main():
    url = await discover_cdp(ports=[9222, 9000, 9001, 9002, 9003])
    conn = CDPConnection(url)
    await conn.connect()
    print("Comparing containers...")
    result = await conn.evaluate(DEBUG_JS) # Use JSON return implicitly
    print(json.dumps(result, indent=2))
    await conn.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
