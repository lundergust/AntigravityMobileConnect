import { useState, useEffect, useCallback } from 'react';
import { useApi } from '../hooks/useApi';

interface FileChange {
    path: string;
    status: string;
    status_code: string;
}

interface ChangesData {
    has_git: boolean;
    files: FileChange[];
    total?: number;
    message?: string;
}

interface DiffData {
    file: string;
    diff: string;
    has_diff: boolean;
}

/**
 * Mobile-optimized diff review panel.
 * Lists changed files with status badges, shows unified diffs,
 * and provides per-file and batch approve/reject controls.
 */
export default function ReviewChanges() {
    const api = useApi();
    const [changes, setChanges] = useState<ChangesData | null>(null);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [diffContent, setDiffContent] = useState<DiffData | null>(null);
    const [loading, setLoading] = useState(false);

    const fetchChanges = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.get<ChangesData>('/chat/changes');
            setChanges(data);
        } catch {
            setChanges({ has_git: false, files: [], message: 'Failed to fetch changes.' });
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchChanges();
    }, [fetchChanges]);

    const handleFileClick = async (filePath: string) => {
        if (selectedFile === filePath) {
            setSelectedFile(null);
            setDiffContent(null);
            return;
        }
        setSelectedFile(filePath);
        try {
            const data = await api.get<DiffData>(`/chat/changes/${encodeURIComponent(filePath)}`);
            setDiffContent(data);
        } catch {
            setDiffContent({ file: filePath, diff: 'Failed to load diff.', has_diff: false });
        }
    };

    const handleReview = async (filePath: string, action: string) => {
        try {
            await api.post('/chat/changes/review', { file: filePath, action });
            await fetchChanges();
            if (selectedFile === filePath) {
                setSelectedFile(null);
                setDiffContent(null);
            }
        } catch {
            // Error handled silently
        }
    };

    const handleReviewAll = async (action: string) => {
        try {
            await api.post('/chat/changes/review-all', { action });
            await fetchChanges();
            setSelectedFile(null);
            setDiffContent(null);
        } catch {
            // Error handled silently
        }
    };

    const statusBadge = (status: string) => {
        const styles: Record<string, { bg: string; color: string; label: string }> = {
            modified: { bg: 'var(--color-warning)', color: 'var(--bg-primary)', label: 'M' },
            added: { bg: 'var(--color-success)', color: 'var(--bg-primary)', label: 'A' },
            deleted: { bg: 'var(--color-danger)', color: 'white', label: 'D' },
            untracked: { bg: 'var(--color-info)', color: 'var(--bg-primary)', label: '?' },
            renamed: { bg: 'var(--accent-secondary)', color: 'var(--bg-primary)', label: 'R' },
        };
        const s = styles[status] || styles.modified;
        return (
            <span
                className="review-changes__badge"
                style={{ background: s.bg, color: s.color }}
            >
                {s.label}
            </span>
        );
    };

    if (loading && !changes) {
        return (
            <div className="review-changes__loading">
                <span className="typing-indicator__dot" />
                <span className="typing-indicator__dot" />
                <span className="typing-indicator__dot" />
                <span style={{ marginLeft: '8px', color: 'var(--text-secondary)' }}>Loading changes…</span>
            </div>
        );
    }

    if (!changes?.has_git) {
        return (
            <div className="review-changes__empty">
                <div style={{ fontSize: '2rem', marginBottom: 'var(--space-sm)' }}>📂</div>
                <p>{changes?.message || 'No git repository detected in current workspace.'}</p>
            </div>
        );
    }

    if (changes.files.length === 0) {
        return (
            <div className="review-changes__empty">
                <div style={{ fontSize: '2rem', marginBottom: 'var(--space-sm)' }}>✨</div>
                <p>No pending changes. Working tree is clean.</p>
            </div>
        );
    }

    return (
        <div className="review-changes">
            {/* Batch actions */}
            <div className="review-changes__batch">
                <span className="review-changes__count">
                    {changes.files.length} file{changes.files.length !== 1 ? 's' : ''} changed
                </span>
                <div className="review-changes__batch-btns">
                    <button
                        className="btn btn--sm btn--success"
                        onClick={() => handleReviewAll('approve')}
                    >
                        ✓ Approve All
                    </button>
                    <button
                        className="btn btn--sm btn--danger"
                        onClick={() => handleReviewAll('reject')}
                    >
                        ✕ Reject All
                    </button>
                </div>
            </div>

            {/* File list */}
            <div className="review-changes__list">
                {changes.files.map((file) => (
                    <div key={file.path} className="review-changes__file-group">
                        <button
                            className={`review-changes__file ${selectedFile === file.path ? 'review-changes__file--active' : ''}`}
                            onClick={() => handleFileClick(file.path)}
                        >
                            {statusBadge(file.status)}
                            <span className="review-changes__filename">{file.path}</span>
                            <span className="review-changes__chevron">
                                {selectedFile === file.path ? '▼' : '▶'}
                            </span>
                        </button>

                        {/* Diff viewer */}
                        {selectedFile === file.path && diffContent && (
                            <div className="review-changes__diff-container">
                                <div className="review-changes__diff-actions">
                                    <button
                                        className="btn btn--sm btn--success"
                                        onClick={() => handleReview(file.path, 'approve')}
                                    >
                                        ✓ Approve
                                    </button>
                                    <button
                                        className="btn btn--sm btn--danger"
                                        onClick={() => handleReview(file.path, 'reject')}
                                    >
                                        ✕ Reject
                                    </button>
                                </div>
                                <pre className="review-changes__diff">
                                    {diffContent.diff
                                        ? diffContent.diff.split('\n').map((line, i) => (
                                            <div
                                                key={i}
                                                className={
                                                    line.startsWith('+') && !line.startsWith('+++')
                                                        ? 'diff-line diff-line--added'
                                                        : line.startsWith('-') && !line.startsWith('---')
                                                            ? 'diff-line diff-line--removed'
                                                            : line.startsWith('@@')
                                                                ? 'diff-line diff-line--hunk'
                                                                : 'diff-line'
                                                }
                                            >
                                                {line}
                                            </div>
                                        ))
                                        : 'No diff available (new/untracked file).'
                                    }
                                </pre>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
