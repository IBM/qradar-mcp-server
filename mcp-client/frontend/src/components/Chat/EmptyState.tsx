import { Button } from '@carbon/react';
import { Security, Add } from '@carbon/icons-react';
import { useUIStore } from '../../store';

interface EmptyStateProps {
  onNewChat: () => void;
}

export default function EmptyState({ onNewChat }: EmptyStateProps) {
  const { openSettings } = useUIStore();

  return (
    <div className="empty-state">
      <Security size={64} className="empty-state__icon" />
      <h1 className="empty-state__title">IBM MCP Client</h1>
      <p className="empty-state__description">
        Chat with your QRadar SIEM using natural language. Ask about offenses, 
        search events, manage reference data, and more.
      </p>
      
      <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
        <Button kind="primary" renderIcon={Add} onClick={onNewChat}>
          Start a conversation
        </Button>
        <Button kind="tertiary" onClick={() => openSettings('qradar')}>
          Configure connections
        </Button>
      </div>

      <div style={{ marginTop: '2rem', fontSize: '0.875rem', color: 'var(--cds-text-secondary)' }}>
        <strong>Example questions:</strong>
        <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
          <li>Show me all open offenses from the last 24 hours</li>
          <li>Search for events with username "admin"</li>
          <li>What reference sets do we have?</li>
          <li>Get the status of our QRadar system</li>
        </ul>
      </div>
    </div>
  );
}
