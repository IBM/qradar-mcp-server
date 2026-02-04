import { useState, useEffect } from 'react';
import {
  Button,
  TextInput,
  Toggle,
  IconButton,
  InlineNotification,
  Dropdown,
} from '@carbon/react';
import { Add, Edit, TrashCan } from '@carbon/icons-react';
import { useConnectionStore } from '../../store';
import type { QRadarConnection } from '../../types';

const PRODUCT_TYPES = [
  { id: 'qradar', label: 'QRadar' },
  { id: 'guardium', label: 'Guardium Data Protection' },
  { id: 'soar', label: 'IBM SOAR' },
];

export default function QRadarConnectionsPanel() {
  const { qradarConnections, addQRadarConnection, updateQRadarConnection, deleteQRadarConnection } = useConnectionStore();
  
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [localConnections, setLocalConnections] = useState<QRadarConnection[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState(PRODUCT_TYPES[0]);
  const [form, setForm] = useState<Partial<QRadarConnection>>({
    name: '',
    url: '',
    token: '',
    verify: true,
    isDefault: false,
  });
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Fetch QRadar connections from backend on mount
  useEffect(() => {
    const fetchConnections = async () => {
      try {
        const response = await fetch('/api/connections/qradar');
        if (response.ok) {
          const connections = await response.json();
          setLocalConnections(connections);
        }
      } catch (error) {
        console.error('Failed to fetch QRadar connections:', error);
        setLocalConnections(qradarConnections);
      }
    };
    fetchConnections();
  }, []);

  // Use localConnections (from backend) instead of qradarConnections (from store)
  const displayConnections = localConnections.length > 0 ? localConnections : qradarConnections;

  const resetForm = () => {
    setForm({ name: '', url: '', token: '', verify: true, isDefault: false });
    setSelectedProduct(PRODUCT_TYPES[0]);
    setIsAdding(false);
    setEditingId(null);
    setTestResult(null);
  };

  const handleSave = async () => {
    if (!form.name || !form.url || !form.token) return;
    
    try {
      const url = editingId 
        ? `/api/connections/qradar/${editingId}`
        : '/api/connections/qradar';
      
      const response = await fetch(url, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      
      if (response.ok) {
        const savedConn = await response.json();
        // Refresh from backend
        const refreshResponse = await fetch('/api/connections/qradar');
        if (refreshResponse.ok) {
          const connections = await refreshResponse.json();
          setLocalConnections(connections);
        }
        if (editingId) {
          updateQRadarConnection(editingId, savedConn);
        } else {
          addQRadarConnection(savedConn);
        }
        
        // Show success message
        setSuccessMessage(editingId ? 'QRadar connection updated successfully!' : 'QRadar connection saved successfully!');
        setTimeout(() => setSuccessMessage(null), 3000);
        
        resetForm();
      }
    } catch (error) {
      console.error('Failed to save connection:', error);
    }
  };

  const handleEdit = (conn: QRadarConnection) => {
    setForm(conn);
    setEditingId(conn.id);
    setIsAdding(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this connection?')) return;
    
    try {
      const response = await fetch(`/api/connections/qradar/${id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        deleteQRadarConnection(id);
      }
    } catch (error) {
      console.error('Failed to delete connection:', error);
      deleteQRadarConnection(id);
    }
  };

  const handleTest = async () => {
    setTestResult(null);
    
    if (!form.url || !form.token) {
      setTestResult({ success: false, message: 'URL and API Token are required' });
      return;
    }

    try {
      const response = await fetch('/api/connections/qradar/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: form.url,
          token: form.token,
          verify: form.verify ?? false,
        }),
      });
      const result = await response.json();
      setTestResult({
        success: result.success,
        message: result.success 
          ? `Connected! QRadar version: ${result.version || 'unknown'}`
          : result.message || 'Connection failed',
      });
    } catch (error) {
      setTestResult({ success: false, message: 'Failed to reach backend API' });
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
            Add Connection
          </Button>

          <div style={{ marginTop: '1rem' }}>
            {displayConnections.length === 0 ? (
              <p style={{ color: 'var(--cds-text-secondary)' }}>
                No QRadar connections configured yet.
              </p>
            ) : (
              displayConnections.map((conn) => (
                <div key={conn.id} className="connection-card">
                  <div className="connection-card__header">
                    <span className="connection-card__name">
                      {conn.name}
                      {conn.isDefault && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--cds-support-info)' }}>(default)</span>}
                    </span>
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      <IconButton kind="ghost" size="sm" label="Edit" onClick={() => handleEdit(conn)}>
                        <Edit />
                      </IconButton>
                      <IconButton kind="ghost" size="sm" label="Delete" onClick={() => handleDelete(conn.id)}>
                        <TrashCan />
                      </IconButton>
                    </div>
                  </div>
                  <div className="connection-card__url">{conn.url}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginTop: '0.25rem' }}>
                    SSL Verify: {conn.verify ? 'Yes' : 'No'}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : (
        <div>
          <h4 style={{ marginBottom: '1rem' }}>{editingId ? 'Edit Connection' : 'Add Connection'}</h4>
          
          <Dropdown
            id="product-type"
            titleText="Product Type"
            label="Select product"
            items={PRODUCT_TYPES}
            itemToString={(item) => item?.label || ''}
            selectedItem={selectedProduct}
            onChange={({ selectedItem }) => selectedItem && setSelectedProduct(selectedItem)}
            style={{ marginBottom: '1rem' }}
          />
          
          <TextInput
            id="conn-name"
            labelText="Name"
            placeholder="Production QRadar"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            style={{ marginBottom: '1rem' }}
          />
          
          <TextInput
            id="conn-url"
            labelText="URL"
            placeholder="https://qradar.example.com"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            style={{ marginBottom: '1rem' }}
          />
          
          <TextInput
            id="conn-token"
            type="password"
            labelText="API Token"
            placeholder="Enter API token"
            value={form.token}
            onChange={(e) => setForm({ ...form, token: e.target.value })}
            style={{ marginBottom: '1rem' }}
          />
          
          <div style={{ marginBottom: '1rem' }}>
            <Toggle
              id="conn-verify"
              labelText="SSL Certificate Verification (disable for self-signed certs)"
              labelA="Off"
              labelB="On"
              toggled={form.verify}
              onToggle={(checked) => setForm({ ...form, verify: checked })}
            />
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <Toggle
              id="conn-default"
              labelText="Default Connection (used for new chats)"
              labelA="No"
              labelB="Yes"
              toggled={form.isDefault}
              onToggle={(checked) => setForm({ ...form, isDefault: checked })}
            />
          </div>

          {testResult && (
            <InlineNotification
              kind={testResult.success ? 'success' : 'error'}
              title={testResult.success ? 'Success' : 'Error'}
              subtitle={testResult.message}
              lowContrast
              style={{ marginBottom: '1rem' }}
            />
          )}

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button kind="secondary" onClick={handleTest}>
              Test Connection
            </Button>
            <Button kind="primary" onClick={handleSave} disabled={!form.name || !form.url || !form.token}>
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
