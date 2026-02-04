import { useState } from 'react';
import { IconButton, TextInput } from '@carbon/react';
import { Edit, TrashCan, Checkmark, Close, Chat } from '@carbon/icons-react';
import { useChatStore } from '../../store';
import type { Chat as ChatType } from '../../types';

interface ChatHistoryItemProps {
  chat: ChatType;
  isActive: boolean;
  onSelect: () => void;
}

export default function ChatHistoryItem({ chat, isActive, onSelect }: ChatHistoryItemProps) {
  const { renameChat, deleteChat } = useChatStore();
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(chat.title);

  const handleRename = () => {
    if (editTitle.trim()) {
      renameChat(chat.id, editTitle.trim());
    }
    setIsEditing(false);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this chat?')) {
      deleteChat(chat.id);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRename();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setEditTitle(chat.title);
    }
  };

  if (isEditing) {
    return (
      <div className={`chat-history__item ${isActive ? 'active' : ''}`}>
        <TextInput
          id={`rename-${chat.id}`}
          labelText=""
          hideLabel
          size="sm"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          style={{ flex: 1 }}
        />
        <IconButton kind="ghost" size="sm" label="Save" onClick={handleRename}>
          <Checkmark />
        </IconButton>
        <IconButton kind="ghost" size="sm" label="Cancel" onClick={() => setIsEditing(false)}>
          <Close />
        </IconButton>
      </div>
    );
  }

  return (
    <div
      className={`chat-history__item ${isActive ? 'active' : ''}`}
      onClick={onSelect}
    >
      <Chat size={16} style={{ flexShrink: 0, marginRight: '0.5rem' }} />
      <span className="chat-history__item-title">{chat.title}</span>
      <div className="chat-history__item-actions">
        <IconButton
          kind="ghost"
          size="sm"
          label="Rename"
          onClick={(e) => {
            e.stopPropagation();
            setIsEditing(true);
          }}
        >
          <Edit />
        </IconButton>
        <IconButton kind="ghost" size="sm" label="Delete" onClick={handleDelete}>
          <TrashCan />
        </IconButton>
      </div>
    </div>
  );
}
