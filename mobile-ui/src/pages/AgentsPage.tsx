import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';

interface Agent {
    id: string;
    name: string;
    file: string;
    status: string;
}

const AGENT_ICONS: Record<string, string> = {
    router: '🧭',
    coder: '💻',
    reviewer: '🔍',
    researcher: '📚',
    base: '🤖',
};

/**
 * Agents page — discover and deploy agents.
 */
export default function AgentsPage() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [swarmTask, setSwarmTask] = useState('');
    const api = useApi();

    useEffect(() => {
        api.get<Agent[]>('/agents/').then(setAgents).catch(() => { });
    }, []);

    const handleDeploy = async (agentId: string) => {
        await api.post(`/agents/${agentId}/deploy`, {});
        setAgents(prev =>
            prev.map(a => a.id === agentId ? { ...a, status: 'running' } : a)
        );
    };

    const handleSwarmDeploy = async () => {
        if (!swarmTask.trim()) return;
        await api.post('/agents/swarm/deploy', { task: swarmTask });
        setSwarmTask('');
    };

    return (
        <div className="page">
            <h1 className="page__title">🤖 Agents</h1>

            {/* Agent Grid */}
            <div className="agent-grid">
                {agents.map(agent => (
                    <div key={agent.id} className="card agent-card">
                        <div className="agent-card__icon">
                            {AGENT_ICONS[agent.id.replace('_agent', '')] || '🤖'}
                        </div>
                        <div className="agent-card__name">{agent.name}</div>
                        <div className="agent-card__role mono">{agent.id}</div>
                        <div className="agent-card__status">
                            <span
                                className="status-dot"
                                style={{
                                    width: 6, height: 6,
                                    background: agent.status === 'running'
                                        ? 'var(--color-success)'
                                        : 'var(--text-muted)',
                                }}
                            />
                            {agent.status}
                        </div>
                        <button
                            className="btn btn--primary btn--sm"
                            style={{ marginTop: 'var(--space-md)', width: '100%' }}
                            onClick={() => handleDeploy(agent.id)}
                        >
                            🚀 Deploy
                        </button>
                    </div>
                ))}
            </div>

            {/* Swarm Deploy */}
            <div className="card" style={{ marginTop: 'var(--space-lg)' }}>
                <div className="card__header">
                    <div>
                        <div className="card__title">🪐 Deploy Agent Swarm</div>
                        <div className="card__subtitle">Launch all specialist agents as a coordinated team</div>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                    <input
                        className="chat-input"
                        placeholder="Describe the swarm task..."
                        value={swarmTask}
                        onChange={e => setSwarmTask(e.target.value)}
                        style={{ borderRadius: 'var(--radius-md)' }}
                    />
                    <button
                        className="btn btn--primary"
                        onClick={handleSwarmDeploy}
                        disabled={!swarmTask.trim()}
                    >
                        🚀 Launch
                    </button>
                </div>
            </div>
        </div>
    );
}
