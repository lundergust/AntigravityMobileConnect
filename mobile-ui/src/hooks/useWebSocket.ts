import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
    type: string;
    data?: unknown;
    message?: string;
    message_id?: string;
    chunk?: string;
    content?: string;
    action?: string;
    messages?: Array<{ id: string; role: string; content: string }>;
    count?: number;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    cdpConnected: boolean;
    lastMessage: WebSocketMessage | null;
    sendMessage: (message: WebSocketMessage) => void;
    sendChatMessage: (message: string) => void;
    sendAction: (action: string, params?: Record<string, unknown>) => void;
    stopGeneration: () => void;
    isStreaming: boolean;
    streamingMessageId: string | null;
}

/**
 * Custom hook for WebSocket connection management.
 * Phase 1: Adds streaming support, chat/action shortcuts, and stream state tracking.
 * Auto-reconnects on disconnect with exponential backoff.
 */
export function useWebSocket(url?: string): UseWebSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const [cdpConnected, setCdpConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
    const reconnectAttempts = useRef(0);

    const getWsUrl = useCallback(() => {
        if (url) return url;
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${proto}//${window.location.host}/ws`;
    }, [url]);

    const connect = useCallback(() => {
        try {
            const ws = new WebSocket(getWsUrl());

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttempts.current = 0;
            };

            ws.onmessage = (event) => {
                try {
                    const data: WebSocketMessage = JSON.parse(event.data);

                    // Track streaming state
                    if (data.type === 'stream_start') {
                        setIsStreaming(true);
                        setStreamingMessageId(data.message_id || null);
                    } else if (data.type === 'stream_end') {
                        setIsStreaming(false);
                        setStreamingMessageId(null);
                    }

                    // Track CDP connection state
                    if (data.type === 'cdp_status' && data.data) {
                        setCdpConnected((data.data as { connected?: boolean }).connected || false);
                    }

                    setLastMessage(data);
                } catch {
                    console.warn('Invalid WebSocket message:', event.data);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                setIsStreaming(false);
                setStreamingMessageId(null);
                wsRef.current = null;
                // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
                const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
                reconnectAttempts.current += 1;
                reconnectTimer.current = setTimeout(connect, delay);
            };

            ws.onerror = () => {
                ws.close();
            };

            wsRef.current = ws;
        } catch {
            // Will retry via onclose handler
        }
    }, [getWsUrl]);

    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [connect]);

    const sendMessage = useCallback((message: WebSocketMessage) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        }
    }, []);

    const sendChatMessage = useCallback((message: string) => {
        sendMessage({ type: 'chat_send', message });
    }, [sendMessage]);

    const sendAction = useCallback((action: string, params?: Record<string, unknown>) => {
        sendMessage({ type: 'action', action, ...params });
    }, [sendMessage]);

    const stopGeneration = useCallback(() => {
        sendMessage({ type: 'stop_generation' });
    }, [sendMessage]);

    return {
        isConnected,
        cdpConnected,
        lastMessage,
        sendMessage,
        sendChatMessage,
        sendAction,
        stopGeneration,
        isStreaming,
        streamingMessageId,
    };
}
