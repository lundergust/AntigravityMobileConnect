import { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import ChatPage from './pages/ChatPage';
import AgentsPage from './pages/AgentsPage';
import QuotaPage from './pages/QuotaPage';
import SettingsPage from './pages/SettingsPage';
import HistoryPage from './pages/HistoryPage';

type Page = 'chat' | 'history' | 'agents' | 'quota' | 'settings';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const NAV_ITEMS: { id: Page; icon: string; label: string }[] = [
  { id: 'chat', icon: '💬', label: 'Chat' },
  { id: 'history', icon: '📜', label: 'History' },
  { id: 'agents', icon: '🤖', label: 'Agents' },
  { id: 'quota', icon: '📊', label: 'Quota' },
  { id: 'settings', icon: '⚙️', label: 'Settings' },
];

/**
 * Root application shell with top nav, page routing, and bottom nav.
 */
export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('chat');
  const [loadedMessages, setLoadedMessages] = useState<ChatMessage[]>([]);
  const [loadedTitle, setLoadedTitle] = useState('');
  const { isConnected } = useWebSocket();

  const handleOpenChat = (messages: ChatMessage[], title: string) => {
    setLoadedMessages(messages);
    setLoadedTitle(title);
    setCurrentPage('chat');
  };

  const handleClearLoaded = () => {
    setLoadedMessages([]);
    setLoadedTitle('');
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'chat':
        return (
          <ChatPage
            loadedMessages={loadedMessages}
            loadedTitle={loadedTitle}
            onClearLoaded={handleClearLoaded}
          />
        );
      case 'history':
        return <HistoryPage onOpenChat={handleOpenChat} />;
      case 'agents':
        return <AgentsPage />;
      case 'quota':
        return <QuotaPage />;
      case 'settings':
        return <SettingsPage />;
    }
  };

  return (
    <div className="app-shell">
      {/* Top Navigation */}
      <nav className="top-nav">
        <div className="top-nav__logo">
          <span className="top-nav__logo-icon">🪐</span>
          <span>Antigravity</span>
        </div>
        <div className="top-nav__status">
          <span
            className={`status-dot ${isConnected ? 'status-dot--connected' : 'status-dot--disconnected'}`}
          />
          <span>{isConnected ? 'Connected' : 'Offline'}</span>
        </div>
      </nav>

      {/* Page Content */}
      <main className="main-content">
        {renderPage()}
      </main>

      {/* Bottom Navigation */}
      <nav className="bottom-nav">
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            className={`bottom-nav__item ${currentPage === item.id ? 'bottom-nav__item--active' : ''}`}
            onClick={() => setCurrentPage(item.id)}
          >
            <span className="bottom-nav__icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
