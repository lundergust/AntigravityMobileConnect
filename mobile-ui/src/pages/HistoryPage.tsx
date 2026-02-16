import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';

interface Conversation {
    id: string;
    title: string;
    created_at: string;
    message_count: number;
    preview: string;
}

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface HistoryPageProps {
    onOpenChat: (messages: ChatMessage[], title: string) => void;
}

/**
 * Chat history page — browse, search, and reopen old conversations.
 */
export default function HistoryPage({ onOpenChat }: HistoryPageProps) {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const api = useApi();

    const fetchHistory = async () => {
        setLoading(true);
        try {
            const data = await api.get<Conversation[]>('/history/');
            setConversations(data);
        } catch {
            // History dir may not exist yet
            setConversations([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

    const handleOpen = async (id: string) => {
        try {
            const data = await api.get<{ title: string; messages: ChatMessage[] }>(`/history/${id}`);
            onOpenChat(data.messages, data.title);
        } catch {
            // Failed to load
        }
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await api.del(`/history/${id}`);
            setConversations(prev => prev.filter(c => c.id !== id));
        } catch {
            // Failed to delete
        }
    };

    const handleSaveCurrent = async () => {
        try {
            await api.post('/history/save', { title: `Chat ${new Date().toLocaleString()}` });
            fetchHistory();
        } catch {
            // Failed to save
        }
    };

    const filtered = conversations.filter(c =>
        c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.preview.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const formatDate = (iso: string) => {
        try {
            const d = new Date(iso);
            const now = new Date();
            const diffMs = now.getTime() - d.getTime();
            const diffMins = Math.floor(diffMs / 60000);
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            const diffHours = Math.floor(diffMins / 60);
            if (diffHours < 24) return `${diffHours}h ago`;
            const diffDays = Math.floor(diffHours / 24);
            if (diffDays < 7) return `${diffDays}d ago`;
            return d.toLocaleDateString();
        } catch {
            return '';
        }
    };

    return (
        <div className="page">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
                <h1 className="page__title" style={{ marginBottom: 0 }}>📜 Chat History</h1>
                <button
                    className="btn btn--primary btn--sm"
                    onClick={handleSaveCurrent}
                    title="Save current chat"
                >
                    💾 Save Current
                </button>
            </div>

            {/* Search */}
            <input
                className="chat-input"
                type="text"
                placeholder="🔍 Search conversations..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{
                    borderRadius: 'var(--radius-md)',
                    marginBottom: 'var(--space-lg)',
                    width: '100%',
                }}
            />

            {/* Conversation List */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-muted)' }}>
                    Loading conversations...
                </div>
            ) : filtered.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-muted)' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-md)' }}>📜</div>
                    <p style={{ fontWeight: 600 }}>No saved conversations</p>
                    <p style={{ fontSize: '0.85rem', marginTop: 'var(--space-sm)' }}>
                        Use the "Save Current" button to save your active chat session.
                    </p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                    {filtered.map(conv => (
                        <div
                            key={conv.id}
                            className="card"
                            onClick={() => handleOpen(conv.id)}
                            style={{
                                cursor: 'pointer',
                                padding: 'var(--space-md)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-md)',
                            }}
                        >
                            <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: 'var(--radius-md)',
                                background: 'var(--accent-gradient)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '1.2rem',
                                flexShrink: 0,
                            }}>
                                💬
                            </div>
                            <div style={{ flex: 1, overflow: 'hidden' }}>
                                <div style={{
                                    fontWeight: 600,
                                    fontSize: '0.9rem',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                }}>
                                    {conv.title}
                                </div>
                                <div style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--text-secondary)',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    marginTop: '2px',
                                }}>
                                    {conv.preview || 'Empty conversation'}
                                </div>
                                <div style={{
                                    fontSize: '0.7rem',
                                    color: 'var(--text-muted)',
                                    marginTop: '4px',
                                    display: 'flex',
                                    gap: 'var(--space-md)',
                                }}>
                                    <span>{formatDate(conv.created_at)}</span>
                                    <span>{conv.message_count} messages</span>
                                </div>
                            </div>
                            <button
                                className="btn btn--ghost btn--sm"
                                onClick={(e) => handleDelete(conv.id, e)}
                                title="Delete conversation"
                                style={{ padding: '4px 8px', fontSize: '0.8rem' }}
                            >
                                🗑️
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
