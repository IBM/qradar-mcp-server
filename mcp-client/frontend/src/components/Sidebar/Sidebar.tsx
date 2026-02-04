import { Button, Search } from '@carbon/react';
import { Add, Chat } from '@carbon/icons-react';
import { useChatStore } from '../../store';
import ChatHistoryList from './ChatHistoryList';

interface SidebarProps {
  collapsed: boolean;
}

export default function Sidebar({ collapsed }: SidebarProps) {
  const { createChat } = useChatStore();

  const handleNewChat = () => {
    createChat();
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar__header">
        <Button
          kind="primary"
          size="sm"
          renderIcon={Add}
          onClick={handleNewChat}
          style={{ width: '100%' }}
        >
          New Chat
        </Button>
      </div>

      <div className="sidebar__search">
        <Search
          size="sm"
          placeholder="Search chats..."
          labelText="Search"
          closeButtonLabelText="Clear search"
        />
      </div>

      <div className="sidebar__content">
        <ChatHistoryList />
      </div>

      <div className="sidebar__footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--cds-text-secondary)', fontSize: '0.75rem' }}>
          <Chat size={16} />
          <span>IBM MCP Client v1.0</span>
        </div>
      </div>
    </aside>
  );
}
