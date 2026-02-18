import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';

export interface ChatMessage {
    id?: string;
    role: 'user' | 'assistant';
    content: string;
    type?: string;
    isStreaming?: boolean;
}

interface ChatViewProps {
    messages: ChatMessage[];
    streamingContent: string;
    onOpenArtifact?: () => void;
}

// --- Icons ---
const FileIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
        <polyline points="13 2 13 9 20 9"></polyline>
    </svg>
);

// --- Custom Components ---

const ThinkBlock = ({ children }: { children: React.ReactNode }) => {
    const [isExpanded, setIsExpanded] = React.useState(true);
    return (
        <div className="think-block">
            <div
                className="think-header"
                onClick={() => setIsExpanded(!isExpanded)}
                role="button"
                tabIndex={0}
            >
                <span className="think-label">Thinking Process</span>
                <span className={`think-arrow ${isExpanded ? 'expanded' : ''}`}>▼</span>
            </div>
            {isExpanded && <div className="think-content">{children}</div>}
        </div>
    );
};

const TaskCard = ({ content }: { content: string }) => {
    const nameMatch = content.match(/TaskName:\s*([^,]+)/);
    const statusMatch = content.match(/TaskStatus:\s*([^,]+)/);

    const name = nameMatch ? nameMatch[1].trim() : 'Task Update';
    const status = statusMatch ? statusMatch[1].trim() : '';

    return (
        <div className="task-card">
            <div className="task-card__header">
                <span className="task-card__icon">⚙️</span>
                <span className="task-card__title">{name}</span>
            </div>
            {status && <div className="task-card__status">{status}</div>}
        </div>
    );
};

const EditedFileCard = ({ content }: { content: string }) => {
    const fileMatch = content.match(/<target_file>(.*?)<\/target_file>/s);
    const fileName = fileMatch ? fileMatch[1].split(/[\\/]/).pop() : 'File Edited';

    return (
        <div className="file-card">
            <div className="file-card__icon"><FileIcon /></div>
            <div className="file-card__name">{fileName}</div>
            <div className="file-card__badge">Modified</div>
        </div>
    );
};

const ReviewLink = ({ content }: { content: string }) => {
    const match = content.match(/\(Requested review for:\s*(.*?)\)/);
    const fileNames = match ? match[1] : 'Artifact';

    return (
        <div className="review-link">
            <span className="review-link__label">Review Requested:</span>
            <span className="review-link__file">{fileNames}</span>
            <span className="review-link__arrow">→</span>
        </div>
    );
};


// --- Parser Logic ---

const SmartParser = ({ content }: { content: string }) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    const regex = /(<task_boundary[\s\S]*?(?:>[\s\S]*?<\/task_boundary>|\/>))|(<edited_file>[\s\S]*?<\/edited_file>)|(\(Requested review for:.*?\))/g;

    let match;
    while ((match = regex.exec(content)) !== null) {
        if (match.index > lastIndex) {
            const text = content.slice(lastIndex, match.index);
            if (text.trim()) {
                parts.push(
                    <ReactMarkdown
                        key={`md-${lastIndex}`}
                        remarkPlugins={[remarkGfm]}
                        components={{
                            code({ node, inline, className, children, ...props }: any) {
                                const match = /language-(\w+)/.exec(className || '');
                                const isThink = match && match[1] === 'think';
                                if (isThink) return <ThinkBlock>{children}</ThinkBlock>;
                                return !inline && match ? (
                                    <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
                                ) : <code className={className} {...props}>{children}</code>;
                            }
                        }}
                    >
                        {text}
                    </ReactMarkdown>
                );
            }
        }

        const fullMatch = match[0];
        if (match[1]) {
            parts.push(<TaskCard key={`task-${match.index}`} content={fullMatch} />);
        } else if (match[2]) {
            parts.push(<EditedFileCard key={`edit-${match.index}`} content={fullMatch} />);
        } else if (match[3]) {
            parts.push(<ReviewLink key={`review-${match.index}`} content={fullMatch} />);
        }
        lastIndex = regex.lastIndex;
    }

    if (lastIndex < content.length) {
        const text = content.slice(lastIndex);
        if (text.trim()) {
            parts.push(
                <ReactMarkdown
                    key={`md-${lastIndex}`}
                    remarkPlugins={[remarkGfm]}
                    components={{
                        code({ node, inline, className, children, ...props }: any) {
                            const match = /language-(\w+)/.exec(className || '');
                            const isThink = match && match[1] === 'think';
                            if (isThink) return <ThinkBlock>{children}</ThinkBlock>;
                            return !inline && match ? (
                                <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
                            ) : <code className={className} {...props}>{children}</code>;
                        }
                    }}
                >
                    {text}
                </ReactMarkdown>
            );
        }
    }

    return <>{parts}</>;
};


export const ChatView: React.FC<ChatViewProps> = ({ messages, streamingContent, onOpenArtifact: _onOpenArtifact }) => {
    // We use an anchor element to ensure robust scrolling to the "bottom" (newest message).
    // In column-reverse, the "bottom" of the rendered list is the 'start' of the DOM.
    // Actually, let's just use scrollIntoView on the *newest* message (Index 0).

    const bottomAnchorRef = React.useRef<HTMLDivElement>(null);

    React.useLayoutEffect(() => {
        // Scroll to bottom whenever messages change (load, send, receive)
        if (messages.length > 0) {
            const scrollToBottom = () => {
                if (bottomAnchorRef.current) {
                    bottomAnchorRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
                }
            };

            // Try immediately
            scrollToBottom();

            // And fallback for dynamic content loading/images
            setTimeout(scrollToBottom, 100);
        }
    }, [messages.length]); // Run when message count changes

    const effectiveMessages = useMemo(() => {
        return streamingContent
            ? [...messages, { role: 'assistant', content: streamingContent, type: 'streaming' } as ChatMessage]
            : messages;
    }, [messages, streamingContent]);

    const reversedMessages = useMemo(() => {
        return [...effectiveMessages].reverse();
    }, [effectiveMessages]);

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {/* Anchor at the physical top (Oldest)? No.
            In column-reverse, visual order is:
            [... Old ... New]
            DOM order is:
            [New ... Old]
            
            So the "Visual Bottom" corresponds to the First DOM element (Newest).
            Let's put an anchor BEFORE the list (which is visually at the bottom).
        */}
                <div ref={bottomAnchorRef} style={{ height: 1, flexShrink: 0 }} />

                {reversedMessages.map((msg, index) => {
                    const isUser = msg.role === 'user';
                    const isStreaming = msg.type === 'streaming';
                    const key = msg.id || `msg-${index}`;

                    return (
                        <div
                            key={key}
                            className={`message ${isUser ? 'user-message' : 'assistant-message'} ${isStreaming ? 'streaming' : ''}`}
                        >
                            {!isUser && (
                                <div className="message-header">
                                    <span className="role-label" style={{ fontWeight: 600 }}>Antigravity</span>
                                </div>
                            )}

                            <div className="message-content">
                                <SmartParser content={msg.content} />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};
