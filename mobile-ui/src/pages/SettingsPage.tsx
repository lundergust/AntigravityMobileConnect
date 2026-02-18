import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';

interface Workspace {
    name: string;
    path: string;
    active: boolean;
}

interface ModelOption {
    id: string;
    name: string;
    provider: string;
}

/**
 * Settings page — workspace/model selection and preferences.
 */
export default function SettingsPage() {
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [models, setModels] = useState<ModelOption[]>([]);
    const [activeModel, setActiveModel] = useState('');
    const api = useApi();

    useEffect(() => {
        api.get<Workspace[]>('/workspaces').then(setWorkspaces).catch(() => { });
        api.get<ModelOption[]>('/models').then(m => {
            setModels(m);
            if (m.length > 0) setActiveModel(m[0].id);
        }).catch(() => { });
    }, []);

    const handleWorkspaceSelect = async (path: string) => {
        await api.post('/workspace/select', { path });
        setWorkspaces(prev =>
            prev.map(w => ({ ...w, active: w.path === path }))
        );
    };

    const handleModelSelect = async (modelId: string) => {
        setActiveModel(modelId);
        await api.post('/model/select', { model: modelId });
    };

    return (
        <div className="page">
            <h1 className="page__title">⚙️ Settings</h1>

            {/* Model Selection */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div className="card__header">
                    <div className="card__title">🧠 AI Model</div>
                </div>
                <select
                    className="selector"
                    value={activeModel}
                    onChange={e => handleModelSelect(e.target.value)}
                >
                    {models.map(m => (
                        <option key={m.id} value={m.id}>
                            {m.name} ({m.provider})
                        </option>
                    ))}
                </select>
            </div>

            {/* Workspace Selection */}
            <div className="card">
                <div className="card__header">
                    <div className="card__title">📁 Workspace</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                    {workspaces.map(ws => (
                        <button
                            key={ws.path}
                            className={`btn ${ws.active ? 'btn--primary' : 'btn--ghost'}`}
                            style={{
                                justifyContent: 'flex-start',
                                textAlign: 'left',
                            }}
                            onClick={() => handleWorkspaceSelect(ws.path)}
                        >
                            <span>{ws.active ? '✅' : '📂'}</span>
                            <span style={{ flex: 1 }}>
                                <div style={{ fontWeight: 600 }}>{ws.name}</div>
                                <div style={{
                                    fontSize: '0.75rem',
                                    opacity: 0.7,
                                    fontFamily: 'var(--font-mono)',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                    maxWidth: '250px',
                                }}>
                                    {ws.path}
                                </div>
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* About */}
            <div className="card" style={{ marginTop: 'var(--space-lg)', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', marginBottom: 'var(--space-sm)' }}>🪐</div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }} className="text-gradient">
                    Antigravity Mobile Connect
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 'var(--space-xs)' }}>
                    v0.1.1-FIXED · Phase 1 Refinement
                </div>
            </div>
        </div>
    );
}
