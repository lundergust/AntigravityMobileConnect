import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useApi } from '../hooks/useApi';
import { ChatView, type ChatMessage } from '../components/ChatView';
import CommandBar from '../components/CommandBar';
import ReviewChanges from '../components/ReviewChanges';
import ArtifactViewer, { extractArtifacts } from '../components/ArtifactViewer';

type TabId = 'chat' | 'changes' | 'terminal' | 'artifacts';

interface ChatPageProps {
    loadedMessages?: ChatMessage[];
    loadedTitle?: string;
    onClearLoaded?: () => void;
    onNewChat?: () => void;
}

/**
 * Main chat page — composes ChatView, CommandBar, ReviewChanges, and ArtifactViewer.
 * Handles WebSocket streaming, tab switching, and chat session management.
 */
export default function ChatPage({ loadedMessages, loadedTitle, onClearLoaded }: ChatPageProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [streamingContent, setStreamingContent] = useState(''); // New separate state for active stream
    const [expandAll, setExpandAll] = useState(false);
    const [actionMode, setActionMode] = useState('ask');
    const [chatTitle, setChatTitle] = useState('');
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState<TabId>('chat');

    // Refs for buffering
    const streamBuffer = useRef<string>('');
    const streamMsgId = useRef<string | null>(null);

    const { isConnected, lastMessage, isStreaming, sendChatMessage, sendAction } = useWebSocket();
    const api = useApi();

    // Extract artifacts from assistant messages
    // Type coercion needed as ArtifactViewer expects slightly different shape
    const chatArtifacts = useMemo(() => extractArtifacts(messages as any[]), [messages]);

    // Load messages from history when provided
    useEffect(() => {
        if (loadedMessages && loadedMessages.length > 0) {
            setMessages(loadedMessages);
            setChatTitle(loadedTitle || '');
        }
    }, [loadedMessages, loadedTitle]);

    // Handle incoming WebSocket messages for streaming
    useEffect(() => {
        if (!lastMessage) return;

        switch (lastMessage.type) {
            case 'stream_start':
                streamBuffer.current = '';
                streamMsgId.current = lastMessage.message_id || null;
                setStreamingContent(''); // Clear previous stream
                // DO NOT add placeholder to 'messages' yet.
                // ChatView will combine 'messages' + 'streamingContent'.
                break;

            case 'stream_chunk':
                if (lastMessage.chunk) {
                    streamBuffer.current += lastMessage.chunk;
                    setStreamingContent(streamBuffer.current); // Update local stream state
                }
                break;

            case 'stream_end':
                if (streamMsgId.current) {
                    const finalContent = lastMessage.content as string || streamBuffer.current;
                    const finalId = streamMsgId.current;

                    // Now commit the finished message to history
                    setMessages(prev => [
                        ...prev,
                        {
                            id: finalId,
                            role: 'assistant',
                            content: finalContent,
                            isStreaming: false
                        }
                    ]);

                    // Reset stream state
                    setStreamingContent('');
                    streamBuffer.current = '';
                    streamMsgId.current = null;
                }
                break;

            // Legacy support for Phase 0 non-streaming responses
            case 'chat_response':
                if (lastMessage.data) {
                    const data = lastMessage.data as ChatMessage;
                    setMessages(prev => [...prev, { ...data, id: data.id || `legacy-${Date.now()}` }]);
                }
                break;

            case 'action_result':
                // Could show a toast or notification here
                break;

            // CDP snapshot — replace messages with desktop Antigravity state
            case 'snapshot_update':
                if (lastMessage.messages && lastMessage.messages.length > 0) {
                    setMessages(lastMessage.messages.map(m => ({
                        ...m,
                        role: m.role as 'user' | 'assistant',
                        isStreaming: false,
                    })));
                }
                break;
        }
    }, [lastMessage]);

    const handleSend = useCallback(async (message: string) => {
        const msgId = `user-${Date.now().toString(36)}`;
        setMessages(prev => [...prev, { id: msgId, role: 'user', content: message }]);

        // Use WebSocket for streaming response
        sendChatMessage(message);
    }, [sendChatMessage]);

    const handleAction = useCallback((action: string, params?: Record<string, unknown>) => {
        sendAction(action, params);
    }, [sendAction]);

    const handleNewChat = useCallback(async () => {
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
        setMessages([]);
        setChatTitle('');
        setActiveTab('chat');
        if (onClearLoaded) onClearLoaded();
    }, [messages, api, onClearLoaded]);

    const handleOpenArtifact = useCallback(() => {
        setActiveTab('artifacts');
    }, []);

    const TABS: { id: TabId; icon: string; label: string }[] = [
        { id: 'chat', icon: '💬', label: 'Chat' },
        { id: 'changes', icon: '📄', label: 'Changes' },
        { id: 'terminal', icon: '💻', label: 'Terminal' },
        { id: 'artifacts', icon: '📦', label: 'Artifacts' },
    ];

    return (
        <div className="chat-container">
            {/* Chat Header */}
            <div className="chat-header">
                <span className="chat-header__title">
                    {chatTitle ? `📜 ${chatTitle}` : '💬 Current Chat'}
                </span>
                <button
                    className="btn btn--primary btn--sm"
                    onClick={handleNewChat}
                    disabled={saving}
                    style={{ fontSize: '0.75rem', flexShrink: 0 }}
                >
                    {saving ? '💾 Saving...' : '✨ New Chat'}
                </button>
            </div>

            {/* Tab Menu */}
            <div className="tab-menu">
                {TABS.map(tab => (
                    <button
                        key={tab.id}
                        className={`tab-menu__item ${activeTab === tab.id ? 'tab-menu__item--active' : ''}`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <span className="tab-menu__icon">{tab.icon}</span>
                        <span>{tab.label}</span>
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="tab-content">
                {activeTab === 'chat' && (
                    <>
                        <ChatView
                            messages={messages}
                            streamingContent={streamingContent}
                            onOpenArtifact={handleOpenArtifact}
                        />
                        <CommandBar
                            onSend={handleSend}
                            onAction={handleAction}
                            isConnected={isConnected}
                            isStreaming={isStreaming}
                            expandAll={expandAll}
                            onToggleExpand={() => setExpandAll(!expandAll)}
                            actionMode={actionMode}
                            onActionModeChange={setActionMode}
                        />
                    </>
                )}
                {activeTab === 'changes' && <ReviewChanges />}
                {activeTab === 'terminal' && (
                    <div className="terminal-placeholder">
                        <div style={{ fontSize: '2rem', marginBottom: 'var(--space-sm)' }}>💻</div>
                        <p>Terminal output will appear here in a future phase.</p>
                    </div>
                )}
                {activeTab === 'artifacts' && <ArtifactViewer artifacts={chatArtifacts} />}
            </div>
        </div>
    );
}
