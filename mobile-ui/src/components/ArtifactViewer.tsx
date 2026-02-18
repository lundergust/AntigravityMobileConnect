import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export interface ChatArtifact {
    id: string;
    name: string;
    type: 'code' | 'markdown' | 'file' | 'plan' | 'command';
    content: string;
    language?: string;
    sourceMessageId?: string;
}

interface ArtifactViewerProps {
    /** Artifacts extracted from the current chat session */
    artifacts: ChatArtifact[];
}

/**
 * Displays artifacts produced during the current chat session.
 * Artifacts are extracted from assistant messages — code blocks,
 * file references, plans, and commands.
 */
export default function ArtifactViewer({ artifacts }: ArtifactViewerProps) {
    const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

    const getIcon = (type: string): string => {
        const icons: Record<string, string> = {
            code: '📜', markdown: '📄', file: '📎',
            plan: '📋', command: '💻',
        };
        return icons[type] || '📎';
    };

    if (artifacts.length === 0) {
        return (
            <div className="artifact-viewer__empty">
                <div style={{ fontSize: '2rem', marginBottom: 'var(--space-sm)' }}>📦</div>
                <p>No artifacts yet.</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Code blocks and files from the agent will appear here.
                </p>
            </div>
        );
    }

    return (
        <div className="artifact-viewer">
            <div className="artifact-viewer__list">
                {artifacts.map((artifact, i) => (
                    <div key={artifact.id} className="artifact-viewer__item-group">
                        <button
                            className={`artifact-viewer__item ${selectedIdx === i ? 'artifact-viewer__item--active' : ''}`}
                            onClick={() => setSelectedIdx(selectedIdx === i ? null : i)}
                        >
                            <span className="artifact-viewer__icon">
                                {getIcon(artifact.type)}
                            </span>
                            <div className="artifact-viewer__info">
                                <span className="artifact-viewer__name">{artifact.name}</span>
                                <span className="artifact-viewer__size">
                                    {artifact.type}{artifact.language ? ` · ${artifact.language}` : ''}
                                </span>
                            </div>
                            <span className="artifact-viewer__chevron">
                                {selectedIdx === i ? '▼' : '▶'}
                            </span>
                        </button>

                        {/* Content preview */}
                        {selectedIdx === i && (
                            <div className="artifact-viewer__content">
                                {artifact.type === 'markdown' ? (
                                    <div className="artifact-viewer__markdown message__content--markdown">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {artifact.content}
                                        </ReactMarkdown>
                                    </div>
                                ) : (
                                    <pre className="artifact-viewer__code">{artifact.content}</pre>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

/**
 * Extract artifacts from chat messages.
 * Finds fenced code blocks, file paths, and structured content
 * in assistant responses.
 */
export function extractArtifacts(messages: Array<{ id: string; role: string; content: string }>): ChatArtifact[] {
    const artifacts: ChatArtifact[] = [];
    let counter = 0;

    for (const msg of messages) {
        if (msg.role !== 'assistant') continue;

        // Extract fenced code blocks
        const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
        let match;
        while ((match = codeBlockRegex.exec(msg.content)) !== null) {
            counter++;
            const language = match[1] || 'text';
            const code = match[2].trim();

            // Try to infer a name from the first line or language
            let name = `Code block #${counter}`;
            const firstLine = code.split('\n')[0];
            if (firstLine.includes('def ') || firstLine.includes('function ')) {
                const funcMatch = /(?:def|function)\s+(\w+)/.exec(firstLine);
                if (funcMatch) name = `${funcMatch[1]}()`;
            } else if (firstLine.includes('class ')) {
                const classMatch = /class\s+(\w+)/.exec(firstLine);
                if (classMatch) name = `class ${classMatch[1]}`;
            } else if (language === 'bash' || language === 'sh' || language === 'powershell') {
                name = `Command #${counter}`;
            }

            artifacts.push({
                id: `artifact-${msg.id}-${counter}`,
                name,
                type: (language === 'bash' || language === 'sh' || language === 'powershell') ? 'command' : 'code',
                content: code,
                language,
                sourceMessageId: msg.id,
            });
        }

        // Extract file path references (e.g., `path/to/file.py`)
        const fileRefRegex = /`([\w/.\\-]+\.\w{1,6})`/g;
        const seenPaths = new Set<string>();
        while ((match = fileRefRegex.exec(msg.content)) !== null) {
            const path = match[1];
            if (!seenPaths.has(path) && path.includes('.') && !path.startsWith('http')) {
                seenPaths.add(path);
                counter++;
                artifacts.push({
                    id: `file-ref-${msg.id}-${counter}`,
                    name: path.split('/').pop() || path,
                    type: 'file',
                    content: path,
                    sourceMessageId: msg.id,
                });
            }
        }
    }

    return artifacts;
}
