import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
    type: string;
    data?: unknown;
    message?: string;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    lastMessage: WebSocketMessage | null;
    sendMessage: (message: WebSocketMessage) => void;
}

/**
 * Custom hook for WebSocket connection management.
 * Auto-reconnects on disconnect with exponential backoff.
 */
export function useWebSocket(url?: string): UseWebSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
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
                    const data = JSON.parse(event.data);
                    setLastMessage(data);
                } catch {
                    console.warn('Invalid WebSocket message:', event.data);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
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

    return { isConnected, lastMessage, sendMessage };
}
