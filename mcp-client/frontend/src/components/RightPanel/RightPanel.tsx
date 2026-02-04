import { Dropdown, Tag } from '@carbon/react';
import { useConnectionStore } from '../../store';

interface RightPanelProps {
  collapsed: boolean;
}

export default function RightPanel({ collapsed }: RightPanelProps) {
  const { 
    qradarConnections, 
    activeQRadarId, 
    setActiveQRadar,
    mcpServers 
  } = useConnectionStore();

  const activeQRadar = qradarConnections.find(c => c.id === activeQRadarId);

  return (
    <aside className={`right-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="right-panel__section">
        <div className="right-panel__title">QRadar Connection</div>
        {qradarConnections.length > 0 ? (
          <Dropdown
            id="qradar-selector"
            titleText=""
            label="Select QRadar"
            items={qradarConnections}
            itemToString={(item) => item?.name || ''}
            selectedItem={activeQRadar}
            onChange={({ selectedItem }) => setActiveQRadar(selectedItem?.id || null)}
          />
        ) : (
          <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)' }}>
            No QRadar connections configured. Add one in Settings.
          </p>
        )}
        
        {activeQRadar && (
          <div className="connection-card" style={{ marginTop: '0.5rem' }}>
            <div className="connection-card__url">{activeQRadar.url}</div>
            <div className={`connection-card__status ${activeQRadar.status || 'disconnected'}`}>
              <span style={{ 
                width: 8, 
                height: 8, 
                borderRadius: '50%', 
                backgroundColor: activeQRadar.status === 'connected' ? 'var(--cds-support-success)' : 'var(--cds-text-secondary)',
                display: 'inline-block'
              }} />
              {activeQRadar.status || 'Not tested'}
            </div>
          </div>
        )}
      </div>

      <div className="right-panel__section">
        <div className="right-panel__title">MCP Servers</div>
        {mcpServers.length > 0 ? (
          mcpServers.map(server => (
            <div key={server.id} className="connection-card">
              <div className="connection-card__header">
                <span className="connection-card__name">{server.name}</span>
                <Tag type={server.status === 'running' ? 'green' : 'gray'} size="sm">
                  {server.status}
                </Tag>
              </div>
              {server.tools && (
                <div style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>
                  {server.tools.length} tools available
                </div>
              )}
            </div>
          ))
        ) : (
          <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)' }}>
            No MCP servers configured. Add one in Settings.
          </p>
        )}
      </div>
    </aside>
  );
}
