import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';

interface QuotaItem {
    model: string;
    pool: string;
    used: number;
    limit: number;
    unit: string;
    reset_at: string;
}

interface QuotaSettings {
    warning_threshold: number;
    danger_threshold: number;
    auto_refresh_seconds: number;
}

/**
 * Quota dashboard modeled after the Antigravity Cockpit extension.
 */
export default function QuotaPage() {
    const [quotas, setQuotas] = useState<QuotaItem[]>([]);
    const [settings, setSettings] = useState<QuotaSettings | null>(null);
    const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
    const api = useApi();

    const fetchData = async () => {
        const [q, s] = await Promise.all([
            api.get<QuotaItem[]>('/quota/'),
            api.get<QuotaSettings>('/quota/settings'),
        ]);
        setQuotas(q);
        setSettings(s);
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, []);

    const getColor = (used: number, limit: number): string => {
        const pctRemaining = ((limit - used) / limit) * 100;
        if (!settings) return 'var(--color-success)';
        if (pctRemaining <= settings.danger_threshold) return 'var(--color-danger)';
        if (pctRemaining <= settings.warning_threshold) return 'var(--color-warning)';
        return 'var(--color-success)';
    };

    const renderRing = (q: QuotaItem) => {
        const pct = Math.min((q.used / q.limit) * 100, 100);
        const radius = 34;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (pct / 100) * circumference;
        const color = getColor(q.used, q.limit);

        return (
            <div className="quota-ring">
                <svg className="quota-ring__svg" width="80" height="80" viewBox="0 0 80 80">
                    <circle className="quota-ring__bg" cx="40" cy="40" r={radius} />
                    <circle
                        className="quota-ring__fill"
                        cx="40" cy="40" r={radius}
                        stroke={color}
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                    />
                </svg>
                <span className="quota-ring__label" style={{ color }}>
                    {Math.round(pct)}%
                </span>
            </div>
        );
    };

    // Group by pool
    const pools = quotas.reduce<Record<string, QuotaItem[]>>((acc, q) => {
        if (!acc[q.pool]) acc[q.pool] = [];
        acc[q.pool].push(q);
        return acc;
    }, {});

    return (
        <div className="page">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-lg)' }}>
                <h1 className="page__title" style={{ marginBottom: 0 }}>📊 Quota</h1>
                <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
                    <button
                        className={`btn btn--sm ${viewMode === 'card' ? 'btn--primary' : 'btn--ghost'}`}
                        onClick={() => setViewMode('card')}
                    >
                        ⊞
                    </button>
                    <button
                        className={`btn btn--sm ${viewMode === 'list' ? 'btn--primary' : 'btn--ghost'}`}
                        onClick={() => setViewMode('list')}
                    >
                        ☰
                    </button>
                    <button className="btn btn--sm btn--ghost" onClick={fetchData}>🔄</button>
                </div>
            </div>

            {/* Pools */}
            {Object.entries(pools).map(([poolName, items]) => (
                <div key={poolName} style={{ marginBottom: 'var(--space-lg)' }}>
                    <h2 style={{
                        fontSize: '0.9rem',
                        color: 'var(--text-secondary)',
                        marginBottom: 'var(--space-md)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                    }}>
                        {poolName} Pool
                    </h2>

                    {viewMode === 'card' ? (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                            gap: 'var(--space-md)',
                        }}>
                            {items.map(q => (
                                <div key={q.model} className="card" style={{ textAlign: 'center' }}>
                                    {renderRing(q)}
                                    <div style={{
                                        fontSize: '0.9rem',
                                        fontWeight: 600,
                                        marginTop: 'var(--space-sm)',
                                    }}>
                                        {q.model}
                                    </div>
                                    <div style={{
                                        fontSize: '0.8rem',
                                        color: 'var(--text-secondary)',
                                        marginTop: 'var(--space-xs)',
                                    }}>
                                        {q.used.toLocaleString()} / {q.limit.toLocaleString()} {q.unit}
                                    </div>
                                    <div style={{
                                        fontSize: '0.7rem',
                                        color: 'var(--text-muted)',
                                        marginTop: 'var(--space-xs)',
                                    }}>
                                        ~{Math.round((q.limit - q.used) / 24)} remaining/hr
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                            {items.map(q => {
                                const pct = (q.used / q.limit) * 100;
                                const color = getColor(q.used, q.limit);
                                return (
                                    <div key={q.model} className="card" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 'var(--space-md)',
                                        padding: 'var(--space-md)',
                                    }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{q.model}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                {q.used.toLocaleString()} / {q.limit.toLocaleString()}
                                            </div>
                                        </div>
                                        <div style={{
                                            width: '100px',
                                            height: '6px',
                                            background: 'var(--bg-elevated)',
                                            borderRadius: 'var(--radius-full)',
                                            overflow: 'hidden',
                                        }}>
                                            <div style={{
                                                width: `${Math.min(pct, 100)}%`,
                                                height: '100%',
                                                background: color,
                                                borderRadius: 'var(--radius-full)',
                                                transition: 'width var(--transition-slow)',
                                            }} />
                                        </div>
                                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color }}>
                                            {Math.round(pct)}%
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            ))}

            {quotas.length === 0 && (
                <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-muted)' }}>
                    <div style={{ fontSize: '2rem', marginBottom: 'var(--space-md)' }}>📊</div>
                    <p>Loading quota data...</p>
                </div>
            )}
        </div>
    );
}
