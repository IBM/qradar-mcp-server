import { useMemo } from 'react';
import { useChatStore } from '../../store';
import ChatHistoryItem from './ChatHistoryItem';
import type { Chat } from '../../types';

// Group chats by date
function groupChatsByDate(chats: Chat[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  const groups: { title: string; chats: Chat[] }[] = [
    { title: 'Today', chats: [] },
    { title: 'Yesterday', chats: [] },
    { title: 'Previous 7 Days', chats: [] },
    { title: 'Older', chats: [] },
  ];

  chats.forEach((chat) => {
    const chatDate = new Date(chat.updatedAt);
    if (chatDate >= today) {
      groups[0].chats.push(chat);
    } else if (chatDate >= yesterday) {
      groups[1].chats.push(chat);
    } else if (chatDate >= weekAgo) {
      groups[2].chats.push(chat);
    } else {
      groups[3].chats.push(chat);
    }
  });

  return groups.filter((g) => g.chats.length > 0);
}

export default function ChatHistoryList() {
  const { chats, activeChatId, setActiveChat } = useChatStore();

  const groupedChats = useMemo(() => {
    const sortedChats = [...chats].sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
    return groupChatsByDate(sortedChats);
  }, [chats]);

  if (chats.length === 0) {
    return (
      <div style={{ padding: '1rem', color: 'var(--cds-text-secondary)', fontSize: '0.875rem', textAlign: 'center' }}>
        No chats yet. Start a new conversation!
      </div>
    );
  }

  return (
    <div className="chat-history">
      {groupedChats.map((group) => (
        <div key={group.title} className="chat-history__group">
          <div className="chat-history__group-title">{group.title}</div>
          {group.chats.map((chat) => (
            <ChatHistoryItem
              key={chat.id}
              chat={chat}
              isActive={chat.id === activeChatId}
              onSelect={() => setActiveChat(chat.id)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
