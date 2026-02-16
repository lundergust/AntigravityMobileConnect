import { useCallback, useState } from 'react';

const BASE_URL = '/api';

interface ApiOptions {
    method?: string;
    body?: unknown;
}

interface UseApiReturn {
    loading: boolean;
    error: string | null;
    get: <T>(path: string) => Promise<T>;
    post: <T>(path: string, body?: unknown) => Promise<T>;
    del: <T>(path: string) => Promise<T>;
}

/**
 * Lightweight API hook for REST calls to the bridge server.
 */
export function useApi(): UseApiReturn {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const request = useCallback(async <T>(path: string, options: ApiOptions = {}): Promise<T> => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${BASE_URL}${path}`, {
                method: options.method || 'GET',
                headers: { 'Content-Type': 'application/json' },
                body: options.body ? JSON.stringify(options.body) : undefined,
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            return await res.json() as T;
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Unknown error';
            setError(msg);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const get = useCallback(<T>(path: string) => request<T>(path), [request]);
    const post = useCallback(<T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }), [request]);
    const del = useCallback(<T>(path: string) => request<T>(path, { method: 'DELETE' }), [request]);

    return { loading, error, get, post, del };
}
