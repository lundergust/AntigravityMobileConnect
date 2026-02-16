import { useState, useRef, useEffect, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useApi } from '../hooks/useApi';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

interface ChatPageProps {
    loadedMessages?: Message[];
    loadedTitle?: string;
    onClearLoaded?: () => void;
    onNewChat?: () => void;
}

/**
 * Main chat page — send messages and view streaming responses.
 * Auto-saves current conversation to history on "New Chat".
 */
export default function ChatPage({ loadedMessages, loadedTitle, onClearLoaded, onNewChat }: ChatPageProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [expandAll, setExpandAll] = useState(false);
    const [actionMode, setActionMode] = useState('ask');
    const [chatTitle, setChatTitle] = useState('');
    const [saving, setSaving] = useState(false);
    const messagesEnd = useRef<HTMLDivElement>(null);
    const { isConnected, lastMessage } = useWebSocket();
    const api = useApi();

    // Load messages from history when provided
    useEffect(() => {
        if (loadedMessages && loadedMessages.length > 0) {
            setMessages(loadedMessages);
            setChatTitle(loadedTitle || '');
        }
    }, [loadedMessages, loadedTitle]);

    // Handle incoming WebSocket messages
    useEffect(() => {
        if (lastMessage?.type === 'chat_response' && lastMessage.data) {
            const data = lastMessage.data as Message;
            setMessages(prev => [...prev, data]);
        }
    }, [lastMessage]);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;
        const userMsg: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        try {
            const res = await api.post<Message>('/chat/send', { message: input });
            setMessages(prev => [...prev, res]);
        } catch {
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: '⚠️ Failed to reach the agent. Check connection.' },
            ]);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    /**
     * Start a new chat — auto-saves the current conversation first.
     */
    const handleNewChat = useCallback(async () => {
        // Save current messages to history if there are any
        if (messages.length > 0) {
            setSaving(true);
            try {
                await api.post('/history/save', { messages });
            } catch {
                // Save failed, but still allow new chat
            } finally {
                setSaving(false);
            }
        }

        // Clear state
        setMessages([]);
        setChatTitle('');
        setInput('');
        if (onClearLoaded) onClearLoaded();
        if (onNewChat) onNewChat();
    }, [messages, api, onClearLoaded, onNewChat]);

    return (
        <div className="chat-container">
            {/* Chat Header — always-visible New Chat button */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 'var(--space-xs) var(--space-md)',
                background: 'var(--bg-card)',
                borderBottom: '1px solid var(--border-subtle)',
            }}>
                <span style={{
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    color: chatTitle ? 'var(--accent-secondary)' : 'var(--text-secondary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    flex: 1,
                }}>
                    {chatTitle ? `📜 ${chatTitle}` : '💬 Current Chat'}
                </span>
                <button
                    className="btn btn--primary btn--sm"
                    onClick={handleNewChat}
                    disabled={saving}
                    style={{
                        fontSize: '0.75rem',
                        flexShrink: 0,
                    }}
                >
                    {saving ? '💾 Saving...' : '✨ New Chat'}
                </button>
            </div>

            {/* Tab Menu */}
            <div style={{
                display: 'flex',
                gap: 'var(--space-xs)',
                padding: 'var(--space-sm) var(--space-md)',
                background: 'var(--bg-secondary)',
                borderBottom: '1px solid var(--border-subtle)',
            }}>
                <button className="btn btn--ghost btn--sm" style={{ flex: 1 }}>📄 Changes</button>
                <button className="btn btn--ghost btn--sm" style={{ flex: 1 }}>💻 Terminal</button>
                <button className="btn btn--ghost btn--sm" style={{ flex: 1 }}>📦 Artifacts</button>
            </div>

            {/* Action Bar */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-sm)',
                padding: 'var(--space-xs) var(--space-md)',
                background: 'var(--bg-elevated)',
                borderBottom: '1px solid var(--border-subtle)',
                flexWrap: 'wrap',
            }}>
                <button
                    className="btn btn--sm btn--ghost"
                    onClick={() => setExpandAll(!expandAll)}
                    style={{ fontSize: '0.75rem' }}
                >
                    {expandAll ? '🔽 Collapse All' : '▶️ Expand All'}
                </button>

                <select
                    className="selector"
                    style={{ width: 'auto', fontSize: '0.75rem', padding: '4px 28px 4px 8px' }}
                    value={actionMode}
                    onChange={e => setActionMode(e.target.value)}
                >
                    <option value="ask">⏸️ Always Prompt</option>
                    <option value="proceed">▶️ Always Proceed</option>
                </select>

                <div style={{ marginLeft: 'auto', display: 'flex', gap: 'var(--space-xs)' }}>
                    <button className="btn btn--sm btn--success">▶ Run</button>
                    <button className="btn btn--sm btn--danger">✕ Reject</button>
                    <select
                        className="selector"
                        style={{ width: 'auto', fontSize: '0.75rem', padding: '4px 28px 4px 8px' }}
                    >
                        <option>Ask every time</option>
                        <option>Run automatically</option>
                        <option>Reject automatically</option>
                    </select>
                </div>
            </div>

            {/* Messages */}
            <div className="chat-messages">
                {messages.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        padding: 'var(--space-2xl)',
                        color: 'var(--text-muted)',
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: 'var(--space-md)' }}>🪐</div>
                        <p style={{ fontSize: '1rem', fontWeight: 600 }}>Antigravity Mobile Connect</p>
                        <p style={{ fontSize: '0.85rem', marginTop: 'var(--space-sm)' }}>
                            Send a message to start a conversation with your agent.
                        </p>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`message message--${msg.role}`}>
                        <div className="message__content">{msg.content}</div>
                    </div>
                ))}
                <div ref={messagesEnd} />
            </div>

            {/* Input Bar */}
            <div className="chat-input-bar">
                <input
                    className="chat-input"
                    type="text"
                    placeholder={isConnected ? "Message your agent..." : "Reconnecting..."}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={!isConnected && false}
                />
                <button
                    className="chat-send-btn"
                    onClick={handleSend}
                    disabled={!input.trim()}
                    title="Send"
                >
                    ➤
                </button>
            </div>
        </div>
    );
}
