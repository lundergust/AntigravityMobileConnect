import { useState, useRef, useEffect } from 'react';

interface CommandBarProps {
    onSend: (message: string) => void;
    onAction: (action: string, params?: Record<string, unknown>) => void;
    isConnected: boolean;
    isStreaming: boolean;
    expandAll: boolean;
    onToggleExpand: () => void;
    actionMode: string;
    onActionModeChange: (mode: string) => void;
}

/**
 * Sticky bottom command bar with auto-growing textarea, send button,
 * and action controls (Run/Reject/mode dropdown).
 */
export default function CommandBar({
    onSend,
    onAction,
    isConnected,
    isStreaming,
    expandAll,
    onToggleExpand,
    actionMode,
    onActionModeChange,
}: CommandBarProps) {
    const [input, setInput] = useState('');
    const [autoMode, setAutoMode] = useState('ask');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const getAutoModeIcon = (mode: string) => {
        switch (mode) {
            case 'run': return '⚡';
            case 'reject': return '🛑';
            default: return '✋';
        }
    };

    // Auto-grow textarea
    useEffect(() => {
        const ta = textareaRef.current;
        if (ta) {
            ta.style.height = 'auto';
            ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
        }
    }, [input]);

    const handleSend = () => {
        if (!input.trim() || isStreaming) return;
        onSend(input.trim());
        setInput('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="command-bar">
            {/* Action controls */}
            <div className="command-bar__actions">
                <button
                    className="btn btn--sm btn--ghost"
                    onClick={onToggleExpand}
                    style={{ fontSize: '0.75rem' }}
                >
                    {expandAll ? '🔽 Collapse' : '▶️ Expand'}
                </button>

                <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
                    <span style={{ position: 'absolute', left: '10px', pointerEvents: 'none', fontSize: '1rem' }}>
                        {actionMode === 'ask' ? '⏸️' : '▶️'}
                    </span>
                    <select
                        className="selector command-bar__mode-select"
                        value={actionMode}
                        onChange={e => onActionModeChange(e.target.value)}
                        style={{ paddingLeft: '32px' }}
                    >
                        <option value="ask">Always Prompt</option>
                        <option value="proceed">Always Proceed</option>
                    </select>
                </div>

                <div className="command-bar__action-btns">
                    <button
                        className="btn btn--sm btn--success command-bar__run-btn"
                        onClick={() => onAction('run')}
                        disabled={isStreaming}
                    >
                        ⚡ Run
                    </button>
                    <button
                        className="btn btn--sm btn--danger command-bar__reject-btn"
                        onClick={() => onAction('reject')}
                        disabled={isStreaming}
                    >
                        🛑 Reject
                    </button>

                    {/* Visual wrapper for icon + select */}
                    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
                        <span style={{ position: 'absolute', left: '10px', pointerEvents: 'none', fontSize: '1rem' }}>
                            {getAutoModeIcon(autoMode)}
                        </span>
                        <select
                            className="selector command-bar__auto-select"
                            value={autoMode}
                            onChange={(e) => setAutoMode(e.target.value)}
                            style={{ paddingLeft: '32px' }}
                        >
                            <option value="ask">Ask every time</option>
                            <option value="run">Run automatically</option>
                            <option value="reject">Reject automatically</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Input row */}
            <div className="command-bar__input-row">
                <textarea
                    ref={textareaRef}
                    className="command-bar__textarea"
                    placeholder={
                        isStreaming
                            ? 'Agent is responding...'
                            : isConnected
                                ? 'Message your agent...'
                                : 'Reconnecting...'
                    }
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                    disabled={isStreaming}
                />
                <button
                    className="chat-send-btn"
                    onClick={handleSend}
                    disabled={!input.trim() || isStreaming}
                    title="Send"
                >
                    ➤
                </button>
            </div>
        </div>
    );
}
