import { useState } from 'react';
import {
  Modal,
} from '@carbon/react';
import { useUIStore } from '../../store';
import QRadarConnectionsPanel from './QRadarConnectionsPanel';
import MCPServersPanel from './MCPServersPanel';
import ModelsPanel from './ModelsPanel';
import PreferencesPanel from './PreferencesPanel';

export default function SettingsModal() {
  const { settingsOpen, closeSettings } = useUIStore();
  const [activeTab, setActiveTab] = useState(0);

  const tabs = ['Connections', 'MCP Servers', 'LLM Models', 'Preferences'];

  return (
    <Modal
      open={settingsOpen}
      onRequestClose={closeSettings}
      modalHeading="Settings"
      passiveModal
      size="lg"
    >
      <div style={{ minHeight: '500px' }}>
        {/* Custom Tab Bar */}
        <div style={{ 
          display: 'flex', 
          borderBottom: '1px solid var(--cds-border-subtle-01)',
          marginBottom: '1rem'
        }}>
          {tabs.map((tab, idx) => (
            <button
              key={tab}
              onClick={() => setActiveTab(idx)}
              style={{
                padding: '0.75rem 1rem',
                background: activeTab === idx ? 'var(--cds-layer-01)' : 'transparent',
                border: 'none',
                borderBottom: activeTab === idx ? '2px solid var(--cds-border-interactive)' : '2px solid transparent',
                color: activeTab === idx ? 'var(--cds-text-primary)' : 'var(--cds-text-secondary)',
                cursor: 'pointer',
                fontSize: '0.875rem',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div style={{ padding: '1rem' }}>
          {activeTab === 0 && <QRadarConnectionsPanel />}
          {activeTab === 1 && <MCPServersPanel />}
          {activeTab === 2 && <ModelsPanel />}
          {activeTab === 3 && <PreferencesPanel />}
        </div>
      </div>
    </Modal>
  );
}
