import { useState, useEffect } from 'react';
import {
  Button,
  TextInput,
  IconButton,
  Tag,
  Select,
  SelectItem,
  InlineNotification,
  RadioButton,
} from '@carbon/react';
import { Add, Edit, TrashCan, Play, Stop } from '@carbon/icons-react';
import { useConnectionStore } from '../../store';
import type { MCPServer, QRadarConnection } from '../../types';

export default function MCPServersPanel() {
  const { mcpServers, addMCPServer, updateMCPServer, deleteMCPServer } = useConnectionStore();
  
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<Record<string, string>>({});
  const [localServers, setLocalServers] = useState<MCPServer[]>([]);
  const [qradarConnections, setQRadarConnections] = useState<QRadarConnection[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [serverMode, setServerMode] = useState<'container' | 'local' | 'http'>('container');
  const [form, setForm] = useState<Partial<MCPServer & { 
    serverPath: string; 
    containerName: string; 
    containerRuntime: string;
    transport: string;
    serverUrl: string;
  }>>({
    name: '',
    command: 'podman',
    args: ['exec', '-i', 'qradar-mcp-server', 'python', '-m', 'src.server'],
    serverPath: '',
    containerName: 'qradar-mcp-server',
    containerRuntime: 'podman',
    qradarConnectionId: '',
    transport: 'stdio',
    serverUrl: 'http://mcp-server:8001',
  });

  // Fetch MCP servers and QRadar connections from backend on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch MCP servers
        const serversResponse = await fetch('/api/mcp/servers');
        if (serversResponse.ok) {
          const servers = await serversResponse.json();
          setLocalServers(servers);
        }

        // Fetch QRadar connections
        const connectionsResponse = await fetch('/api/connections/qradar');
        if (connectionsResponse.ok) {
          const connections = await connectionsResponse.json();
          setQRadarConnections(connections);
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
        setLocalServers(mcpServers); // Fallback to store
      }
    };
    fetchData();
  }, []);

  // Use localServers (from backend) instead of mcpServers (from store)
  const displayServers = localServers.length > 0 ? localServers : mcpServers;

  const resetForm = () => {
    setForm({ 
      name: '', 
      command: 'podman', 
      args: ['exec', '-i', 'qradar-mcp-server', 'python', '-m', 'src.server'], 
      serverPath: '', 
      containerName: 'qradar-mcp-server',
      containerRuntime: 'podman',
      qradarConnectionId: '',
      transport: 'stdio',
      serverUrl: 'http://mcp-server:8001',
    });
    setServerMode('container');
    setIsAdding(false);
    setEditingId(null);
  };

  const handleSave = async () => {
    if (!form.name) return;
    
    // Build command and args based on mode
    let command = form.command || 'podman';
    let args = form.args || [];
    let transport = 'stdio';
    
    if (serverMode === 'container') {
      command = form.containerRuntime || 'podman';
      args = ['exec', '-i', form.containerName || 'qradar-mcp-server', 'python', '-m', 'src.server'];
      transport = 'stdio';
    } else if (serverMode === 'http') {
      transport = 'http';
    }
    
    try {
      // Save to backend API (which persists to config.json)
      const url = editingId 
        ? `/api/mcp/servers/${editingId}`
        : '/api/mcp/servers';
      
      const response = await fetch(url, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          command: command,
          args: args,
          serverPath: form.serverPath || '',
          containerName: form.containerName,
          containerRuntime: form.containerRuntime,
          serverMode: serverMode,
          transport: transport,
          serverUrl: form.serverUrl || 'http://mcp-server:8001',
          qradarConnectionId: form.qradarConnectionId,
          env: {},
        }),
      });
      
      if (response.ok) {
        const savedServer = await response.json();
        // Refresh from backend to get the actual saved data
        const refreshResponse = await fetch('/api/mcp/servers');
        if (refreshResponse.ok) {
          const servers = await refreshResponse.json();
          setLocalServers(servers);
        }
        // Also update local store
        if (editingId) {
          updateMCPServer(editingId, savedServer);
        } else {
          addMCPServer(savedServer);
        }
        
        // Show success message
        setSuccessMessage(editingId ? 'MCP Server updated successfully!' : 'MCP Server configured successfully!');
        setTimeout(() => setSuccessMessage(null), 3000);
        
        resetForm();
      }
    } catch (error) {
      console.error('Failed to save MCP server:', error);
    }
  };

  const handleEdit = (server: MCPServer) => {
    setForm(server);
    setEditingId(server.id);
    setIsAdding(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this MCP server?')) return;
    
    try {
      // Delete from backend API first
      const response = await fetch(`/api/mcp/servers/${id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        // Then delete from local store
        deleteMCPServer(id);
      }
    } catch (error) {
      console.error('Failed to delete MCP server:', error);
      // Still try to delete from local store
      deleteMCPServer(id);
    }
  };

  const handleToggleServer = async (server: MCPServer) => {
    const action = server.status === 'running' ? 'stop' : 'start';
    setServerStatus(prev => ({ ...prev, [server.id]: 'loading' }));
    
    try {
      await fetch(`/api/mcp/servers/${server.id}/${action}`, {
        method: 'POST',
      });
      
      // Refresh server list to get updated status
      const refreshResponse = await fetch('/api/mcp/servers');
      if (refreshResponse.ok) {
        const servers = await refreshResponse.json();
        setLocalServers(servers);
      }
      
      setServerStatus(prev => ({ ...prev, [server.id]: '' }));
    } catch (error) {
      console.error(`Failed to ${action} server:`, error);
      setServerStatus(prev => ({ ...prev, [server.id]: 'error' }));
      setTimeout(() => setServerStatus(prev => ({ ...prev, [server.id]: '' })), 3000);
    }
  };

  return (

    <div style={{ padding: '1rem' }}>
      {successMessage && (
        <InlineNotification
          kind="success"
          title="Success"
          subtitle={successMessage}
          onClose={() => setSuccessMessage(null)}
          style={{ marginBottom: '1rem' }}
        />
      )}
      
      {!isAdding ? (
        <>
          <Button kind="primary" renderIcon={Add} onClick={() => setIsAdding(true)}>
            Add MCP Server
          </Button>

          <div style={{ marginTop: '1rem' }}>
            {displayServers.length === 0 ? (
              <div>
                <p style={{ color: 'var(--cds-text-secondary)', marginBottom: '1rem' }}>
                  No MCP servers configured yet.
                </p>
                <InlineNotification
                  kind="info"
                  title="Configure MCP Servers"
                  subtitle="MCP servers run in Docker containers on this server. Configure one to get started."
                  lowContrast
                  hideCloseButton
                />
              </div>
            ) : (
              <>
                {displayServers.map((server) => {
                const qradarConn = qradarConnections.find(c => c.id === server.qradarConnectionId);
                const isHttpMode = (server as any).serverMode === 'http' || (server as any).transport === 'http';
                const isContainerMode = !isHttpMode && ((server as any).serverMode === 'container' || (server as any).containerName);
                const containerRunning = (server as any).container_running;
                const isConnected = server.status === 'running';
                return (
                  <div key={server.id} className="connection-card">
                    <div className="connection-card__header">
                      <span className="connection-card__name">{server.name}</span>
                      <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                        {isHttpMode ? (
                          <Tag type="blue" size="sm">HTTP</Tag>
                        ) : isContainerMode && (
                          <Tag type={containerRunning ? 'blue' : 'red'} size="sm">
                            {containerRunning ? 'container running' : 'container stopped'}
                          </Tag>
                        )}
                        <Tag type={isConnected ? 'green' : 'gray'} size="sm">
                          {serverStatus[server.id] === 'loading' ? 'loading...' : 
                           isConnected ? 'connected' : 'disconnected'}
                        </Tag>
                        <IconButton 
                          kind="ghost" 
                          size="sm" 
                          label={isConnected ? (isContainerMode ? 'Disconnect' : 'Stop') : (isContainerMode ? 'Connect' : 'Start')} 
                          onClick={() => handleToggleServer(server)}
                          disabled={serverStatus[server.id] === 'loading' || (isContainerMode && !containerRunning)}
                        >
                          {isConnected ? <Stop /> : <Play />}
                        </IconButton>
                        <IconButton kind="ghost" size="sm" label="Edit" onClick={() => handleEdit(server)}>
                          <Edit />
                        </IconButton>
                        <IconButton kind="ghost" size="sm" label="Delete" onClick={() => handleDelete(server.id)}>
                          <TrashCan />
                        </IconButton>
                      </div>
                    </div>
                    {isHttpMode ? (
                      <div style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginTop: '0.25rem' }}>
                        <strong>URL:</strong> {(server as any).serverUrl || 'Not set'}
                      </div>
                    ) : isContainerMode ? (
                      <div style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginTop: '0.25rem' }}>
                        <strong>Container:</strong> {(server as any).containerName} ({(server as any).containerRuntime || 'podman'})
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginTop: '0.25rem' }}>
                        <strong>Path:</strong> {(server as any).serverPath || 'Not set'}
                      </div>
                    )}
                    <div style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginTop: '0.25rem' }}>
                      <strong>QRadar:</strong> {qradarConn?.name || 'Not selected'}
                    </div>
                    {!isHttpMode && (
                      <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--cds-text-secondary)', marginTop: '0.25rem' }}>
                        {server.command} {server.args?.join(' ')}
                      </div>
                    )}
                  </div>
                );
              })}
              </>
            )}
          </div>
        </>
      ) : (
        <div>
          <h4 style={{ marginBottom: '1rem' }}>{editingId ? 'Edit MCP Server' : 'Add MCP Server'}</h4>
          
          <TextInput
            id="mcp-name"
            labelText="Name"
            placeholder="QRadar MCP Server"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            style={{ marginBottom: '1rem' }}
          />

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 600 }}>
              Server Mode
            </label>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <RadioButton
                labelText="Container (Podman/Docker)"
                value="container"
                id="mode-container"
                checked={serverMode === 'container'}
                onChange={() => setServerMode('container')}
              />
              <RadioButton
                labelText="HTTP/SSE (Network)"
                value="http"
                id="mode-http"
                checked={serverMode === 'http'}
                onChange={() => setServerMode('http')}
              />
              <RadioButton
                labelText="Local Process"
                value="local"
                id="mode-local"
                checked={serverMode === 'local'}
                onChange={() => setServerMode('local')}
              />
            </div>
          </div>

          {serverMode === 'container' ? (
            <>
              <Select
                id="mcp-runtime"
                labelText="Container Runtime"
                value={form.containerRuntime || 'podman'}
                onChange={(e) => setForm({ ...form, containerRuntime: e.target.value })}
                style={{ marginBottom: '1rem' }}
              >
                <SelectItem value="podman" text="Podman" />
                <SelectItem value="docker" text="Docker" />
              </Select>

              <TextInput
                id="mcp-container"
                labelText="Container Name"
                placeholder="qradar-mcp-server"
                value={form.containerName}
                onChange={(e) => setForm({ ...form, containerName: e.target.value })}
                style={{ marginBottom: '1rem' }}
                helperText="Name of the running MCP server container"
              />
            </>
          ) : serverMode === 'http' ? (
            <>
              <TextInput
                id="mcp-url"
                labelText="MCP Server URL"
                placeholder="http://mcp-server:8001"
                value={form.serverUrl}
                onChange={(e) => setForm({ ...form, serverUrl: e.target.value })}
                style={{ marginBottom: '1rem' }}
                helperText="HTTP/SSE endpoint of the MCP server (e.g., http://mcp-server:8001 for container-to-container)"
              />
            </>
          ) : (
            <>
              <TextInput
                id="mcp-path"
                labelText="Server Path (directory containing the MCP server)"
                placeholder="/path/to/QRadar-MCP-Server"
                value={form.serverPath}
                onChange={(e) => setForm({ ...form, serverPath: e.target.value })}
                style={{ marginBottom: '1rem' }}
              />

              <TextInput
                id="mcp-command"
                labelText="Command"
                placeholder="python3"
                value={form.command}
                onChange={(e) => setForm({ ...form, command: e.target.value })}
                style={{ marginBottom: '1rem' }}
              />
              
              <TextInput
                id="mcp-args"
                labelText="Arguments (space-separated)"
                placeholder="-m src.server"
                value={form.args?.join(' ')}
                onChange={(e) => setForm({ ...form, args: e.target.value.split(' ') })}
                style={{ marginBottom: '1rem' }}
              />
            </>
          )}

          <Select
            id="mcp-qradar"
            labelText="QRadar Connection"
            value={form.qradarConnectionId || ''}
            onChange={(e) => setForm({ ...form, qradarConnectionId: e.target.value })}
            style={{ marginBottom: '1rem' }}
            helperText="Link to QRadar connection for credentials"
          >
            <SelectItem value="" text="Select a QRadar connection..." />
            {qradarConnections.map((conn) => (
              <SelectItem key={conn.id} value={conn.id} text={conn.name} />
            ))}
          </Select>

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <Button kind="primary" onClick={handleSave} disabled={!form.name || (serverMode === 'container' && !form.containerName)}>
              {editingId ? 'Update' : 'Save'}
            </Button>
            <Button kind="ghost" onClick={resetForm}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
