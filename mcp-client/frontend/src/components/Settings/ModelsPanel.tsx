import { useState, useMemo, useEffect } from 'react';
import {
  Button,
  TextInput,
  Select,
  SelectItem,
  Toggle,
  IconButton,
  ComboBox,
  InlineNotification,
} from '@carbon/react';
import { Add, Edit, TrashCan } from '@carbon/icons-react';
import { useConnectionStore } from '../../store';
import type { LLMModel } from '../../types';

const PROVIDERS = [
  { id: 'watsonx', name: 'IBM Watsonx' },
  { id: 'openrouter', name: 'OpenRouter' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'anthropic', name: 'Anthropic' },
  { id: 'ollama', name: 'Ollama (Local)' },
];

// All 29 Watsonx models from API
const WATSONX_MODELS = [
  { modelId: 'ibm/granite-3-3-8b-instruct', displayName: 'Granite 3.3 8B Instruct' },
  { modelId: 'ibm/granite-3-2-8b-instruct', displayName: 'Granite 3.2 8B Instruct' },
  { modelId: 'ibm/granite-3-1-8b-base', displayName: 'Granite 3.1 8B Base' },
  { modelId: 'ibm/granite-3-8b-instruct', displayName: 'Granite 3 8B Instruct' },
  { modelId: 'ibm/granite-3-3-8b-instruct-np', displayName: 'Granite 3.3 8B Instruct NP' },
  { modelId: 'ibm/granite-4-h-small', displayName: 'Granite 4 H Small' },
  { modelId: 'ibm/granite-8b-code-instruct', displayName: 'Granite 8B Code Instruct' },
  { modelId: 'ibm/granite-guardian-3-8b', displayName: 'Granite Guardian 3 8B' },
  { modelId: 'ibm/granite-embedding-278m-multilingual', displayName: 'Granite Embedding 278M' },
  { modelId: 'ibm/granite-ttm-1024-96-r2', displayName: 'Granite TTM 1024' },
  { modelId: 'ibm/granite-ttm-1536-96-r2', displayName: 'Granite TTM 1536' },
  { modelId: 'ibm/granite-ttm-512-96-r2', displayName: 'Granite TTM 512' },
  { modelId: 'ibm/slate-125m-english-rtrvr-v2', displayName: 'Slate 125M English' },
  { modelId: 'ibm/slate-30m-english-rtrvr-v2', displayName: 'Slate 30M English' },
  { modelId: 'meta-llama/llama-3-3-70b-instruct', displayName: 'Llama 3.3 70B Instruct' },
  { modelId: 'meta-llama/llama-3-1-70b-gptq', displayName: 'Llama 3.1 70B GPTQ' },
  { modelId: 'meta-llama/llama-3-1-8b', displayName: 'Llama 3.1 8B' },
  { modelId: 'meta-llama/llama-3-2-11b-vision-instruct', displayName: 'Llama 3.2 11B Vision' },
  { modelId: 'meta-llama/llama-3-2-90b-vision-instruct', displayName: 'Llama 3.2 90B Vision' },
  { modelId: 'meta-llama/llama-3-405b-instruct', displayName: 'Llama 3 405B Instruct' },
  { modelId: 'meta-llama/llama-4-maverick-17b-128e-instruct-fp8', displayName: 'Llama 4 Maverick 17B' },
  { modelId: 'meta-llama/llama-guard-3-11b-vision', displayName: 'Llama Guard 3 11B Vision' },
  { modelId: 'mistral-large-2512', displayName: 'Mistral Large' },
  { modelId: 'mistralai/mistral-medium-2505', displayName: 'Mistral Medium' },
  { modelId: 'mistralai/mistral-small-3-1-24b-instruct-2503', displayName: 'Mistral Small 24B' },
  { modelId: 'openai/gpt-oss-120b', displayName: 'GPT OSS 120B' },
  { modelId: 'intfloat/multilingual-e5-large', displayName: 'Multilingual E5 Large' },
  { modelId: 'sentence-transformers/all-minilm-l6-v2', displayName: 'All MiniLM L6 v2' },
  { modelId: 'cross-encoder/ms-marco-minilm-l-12-v2', displayName: 'MS Marco MiniLM L12' },
];

// Popular OpenRouter models
const OPENROUTER_MODELS = [
  // Anthropic Claude Models
  { modelId: 'anthropic/claude-opus-4.5', displayName: 'Claude Opus 4.5' },
  { modelId: 'anthropic/claude-sonnet-4.5', displayName: 'Claude Sonnet 4.5' },
  { modelId: 'anthropic/claude-haiku-4.5', displayName: 'Claude Haiku 4.5' },
  { modelId: 'anthropic/claude-opus-4.1', displayName: 'Claude Opus 4.1' },
  { modelId: 'anthropic/claude-opus-4', displayName: 'Claude Opus 4' },
  { modelId: 'anthropic/claude-sonnet-4', displayName: 'Claude Sonnet 4' },
  { modelId: 'anthropic/claude-3.7-sonnet', displayName: 'Claude 3.7 Sonnet' },
  { modelId: 'anthropic/claude-3.7-sonnet:thinking', displayName: 'Claude 3.7 Sonnet (Thinking)' },
  { modelId: 'anthropic/claude-3.5-sonnet', displayName: 'Claude 3.5 Sonnet' },
  { modelId: 'anthropic/claude-3.5-haiku', displayName: 'Claude 3.5 Haiku' },
  { modelId: 'anthropic/claude-3-opus', displayName: 'Claude 3 Opus' },
  { modelId: 'anthropic/claude-3-sonnet', displayName: 'Claude 3 Sonnet' },
  { modelId: 'anthropic/claude-3-haiku', displayName: 'Claude 3 Haiku' },
  
  // Google Gemini Models
  { modelId: 'google/gemini-3-pro-preview', displayName: 'Gemini 3 Pro (Preview)' },
  { modelId: 'google/gemini-3-flash-preview', displayName: 'Gemini 3 Flash (Preview)' },
  { modelId: 'google/gemini-2.5-pro', displayName: 'Gemini 2.5 Pro' },
  { modelId: 'google/gemini-2.5-flash', displayName: 'Gemini 2.5 Flash' },
  { modelId: 'google/gemini-2.5-flash-lite', displayName: 'Gemini 2.5 Flash Lite' },
  { modelId: 'google/gemini-2.0-flash-001', displayName: 'Gemini 2.0 Flash' },
  { modelId: 'google/gemini-2.0-flash-lite-001', displayName: 'Gemini 2.0 Flash Lite' },
  { modelId: 'google/gemini-2.0-flash-exp:free', displayName: 'Gemini 2.0 Flash (Free)' },
  { modelId: 'google/gemini-pro-1.5', displayName: 'Gemini Pro 1.5' },
  { modelId: 'google/gemini-flash-1.5', displayName: 'Gemini Flash 1.5' },
  { modelId: 'google/gemma-3-27b-it', displayName: 'Gemma 3 27B' },
  { modelId: 'google/gemma-3-12b-it', displayName: 'Gemma 3 12B' },
  { modelId: 'google/gemma-3-4b-it', displayName: 'Gemma 3 4B' },
  { modelId: 'google/gemma-2-27b-it', displayName: 'Gemma 2 27B' },
  { modelId: 'google/gemma-2-9b-it', displayName: 'Gemma 2 9B' },
  
  // OpenAI Models
  { modelId: 'openai/gpt-5.2-pro', displayName: 'GPT-5.2 Pro' },
  { modelId: 'openai/gpt-5.2-chat', displayName: 'GPT-5.2 Chat' },
  { modelId: 'openai/gpt-5.1', displayName: 'GPT-5.1' },
  { modelId: 'openai/gpt-5-mini', displayName: 'GPT-5 Mini' },
  { modelId: 'openai/gpt-5-pro', displayName: 'GPT-5 Pro' },
  { modelId: 'openai/gpt-4o', displayName: 'GPT-4o' },
  { modelId: 'openai/gpt-4o-mini', displayName: 'GPT-4o Mini' },
  { modelId: 'openai/gpt-4-turbo', displayName: 'GPT-4 Turbo' },
  { modelId: 'openai/gpt-4.1', displayName: 'GPT-4.1' },
  { modelId: 'openai/gpt-4.1-mini', displayName: 'GPT-4.1 Mini' },
  { modelId: 'openai/o3-mini', displayName: 'o3 Mini' },
  { modelId: 'openai/o3', displayName: 'o3' },
  { modelId: 'openai/o4-mini', displayName: 'o4 Mini' },
  { modelId: 'openai/o1', displayName: 'o1' },
  { modelId: 'openai/o1-mini', displayName: 'o1 Mini' },
  { modelId: 'openai/gpt-oss-120b:free', displayName: 'GPT OSS 120B (Free)' },
  { modelId: 'openai/gpt-oss-20b:free', displayName: 'GPT OSS 20B (Free)' },
  
  // Meta Llama Models
  { modelId: 'meta-llama/llama-3.3-70b-instruct', displayName: 'Llama 3.3 70B' },
  { modelId: 'meta-llama/llama-3.1-405b-instruct', displayName: 'Llama 3.1 405B' },
  { modelId: 'meta-llama/llama-3.1-70b-instruct', displayName: 'Llama 3.1 70B' },
  { modelId: 'meta-llama/llama-3.1-8b-instruct', displayName: 'Llama 3.1 8B' },
  { modelId: 'meta-llama/llama-3.1-8b-instruct:free', displayName: 'Llama 3.1 8B (Free)' },
  
  // Qwen Models
  { modelId: 'qwen/qwen-3-next-80b-a3b-instruct:free', displayName: 'Qwen3 Next 80B (Free)' },
  { modelId: 'qwen/qwen-3-coder-480b-a35b:free', displayName: 'Qwen3 Coder 480B (Free)' },
  { modelId: 'qwen/qwen-3-4b:free', displayName: 'Qwen3 4B (Free)' },
  { modelId: 'qwen/qwen-2.5-72b-instruct', displayName: 'Qwen 2.5 72B' },
  
  // Mistral Models
  { modelId: 'mistralai/mistral-large', displayName: 'Mistral Large' },
  { modelId: 'mistralai/mistral-medium', displayName: 'Mistral Medium' },
  { modelId: 'mistralai/mistral-small-3.1-24b', displayName: 'Mistral Small 24B' },
  { modelId: 'mistralai/mistral-small-3.1-24b:free', displayName: 'Mistral Small 24B (Free)' },
  { modelId: 'mistralai/mixtral-8x22b-instruct', displayName: 'Mixtral 8x22B' },
  { modelId: 'mistralai/devstral-2-2512:free', displayName: 'Devstral 2 (Free)' },
  
  // DeepSeek Models
  { modelId: 'deepseek/deepseek-chat', displayName: 'DeepSeek Chat' },
  
  // Xiaomi Models
  { modelId: 'xiaomi/mimo-v2-flash:free', displayName: 'MiMo V2 Flash (Free)' },
];

const DEFAULT_MODELS: Record<string, { modelId: string; displayName: string }[]> = {
  watsonx: WATSONX_MODELS,
  openrouter: OPENROUTER_MODELS,
  openai: [
    { modelId: 'gpt-4o', displayName: 'GPT-4o' },
    { modelId: 'gpt-4o-mini', displayName: 'GPT-4o Mini' },
    { modelId: 'gpt-4-turbo', displayName: 'GPT-4 Turbo' },
    { modelId: 'gpt-3.5-turbo', displayName: 'GPT-3.5 Turbo' },
  ],
  anthropic: [
    { modelId: 'claude-sonnet-4-20250514', displayName: 'Claude Sonnet 4' },
    { modelId: 'claude-3-5-sonnet-20241022', displayName: 'Claude 3.5 Sonnet' },
    { modelId: 'claude-3-opus-20240229', displayName: 'Claude 3 Opus' },
  ],
  ollama: [
    { modelId: 'llama3.2', displayName: 'Llama 3.2' },
    { modelId: 'llama3.1', displayName: 'Llama 3.1' },
    { modelId: 'mistral', displayName: 'Mistral' },
    { modelId: 'qwen3:0.6b', displayName: 'Qwen3 0.6B' },
    { modelId: 'codellama', displayName: 'Code Llama' },
  ],
};

// Provider-specific configuration hints
const PROVIDER_CONFIG: Record<string, { 
  apiKeyLabel: string; 
  apiKeyPlaceholder: string;
  showBaseUrl: boolean;
  baseUrlDefault: string;
  showProjectId?: boolean;
}> = {
  watsonx: {
    apiKeyLabel: 'IBM Cloud API Key',
    apiKeyPlaceholder: 'Enter IBM Cloud API key',
    showBaseUrl: true,
    baseUrlDefault: 'https://us-south.ml.cloud.ibm.com',
    showProjectId: true,
  },
  openrouter: {
    apiKeyLabel: 'OpenRouter API Key',
    apiKeyPlaceholder: 'sk-or-...',
    showBaseUrl: false,
    baseUrlDefault: 'https://openrouter.ai/api/v1',
  },
  openai: {
    apiKeyLabel: 'OpenAI API Key',
    apiKeyPlaceholder: 'sk-...',
    showBaseUrl: false,
    baseUrlDefault: 'https://api.openai.com/v1',
  },
  anthropic: {
    apiKeyLabel: 'Anthropic API Key',
    apiKeyPlaceholder: 'sk-ant-...',
    showBaseUrl: false,
    baseUrlDefault: 'https://api.anthropic.com',
  },
  ollama: {
    apiKeyLabel: 'API Key (optional)',
    apiKeyPlaceholder: 'Usually not required for local Ollama',
    showBaseUrl: true,
    baseUrlDefault: 'http://localhost:11434',
  },
};

export default function ModelsPanel() {
  const { models, addModel, updateModel, deleteModel } = useConnectionStore();
  
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [modelSearch, setModelSearch] = useState('');
  const [localModels, setLocalModels] = useState<LLMModel[]>([]);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<LLMModel> & { projectId?: string }>({
    provider: 'watsonx',
    name: '',
    displayName: '',
    modelId: '',
    apiKey: '',
    baseUrl: '',
    isDefault: false,
    projectId: '',
  });

  // Fetch models from backend on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch('/api/connections/models');
        if (response.ok) {
          const modelsData = await response.json();
          // Convert snake_case to camelCase for display
          const normalizedModels = modelsData.map((m: any) => ({
            ...m,
            displayName: m.display_name || m.displayName || m.name,
            modelId: m.model_id || m.modelId,
            apiKey: m.api_key || m.apiKey,
            baseUrl: m.base_url || m.baseUrl,
            isDefault: m.is_default || m.isDefault,
          }));
          setLocalModels(normalizedModels);
        }
      } catch (error) {
        console.error('Failed to fetch models:', error);
        setLocalModels(models);
      }
    };
    fetchModels();
  }, []);

  // Use localModels (from backend) if available
  const displayModels = localModels.length > 0 ? localModels : models;

  const resetForm = () => {
    setForm({ 
      provider: 'watsonx', 
      name: '', 
      displayName: '', 
      modelId: '', 
      apiKey: '', 
      baseUrl: '', 
      isDefault: false,
      projectId: '',
    });
    setModelSearch('');
    setIsAdding(false);
    setEditingId(null);
  };

  const handleSave = async () => {
    if (!form.provider || !form.modelId) return;
    
    const providerConfig = PROVIDER_CONFIG[form.provider];
    
    // Convert to snake_case for backend
    const backendPayload = {
      provider: form.provider,
      name: form.name || form.modelId,
      display_name: form.displayName || form.modelId,
      model_id: form.modelId,
      api_key: form.apiKey || '',
      base_url: form.baseUrl || providerConfig?.baseUrlDefault || '',
      project_id: form.projectId || '',
      is_default: form.isDefault || false,
    };
    
    try {
      const url = editingId 
        ? `/api/connections/models/${editingId}`
        : '/api/connections/models';
      
      const response = await fetch(url, {
        method: editingId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(backendPayload),
      });
      
      if (response.ok) {
        const savedModel = await response.json();
        if (editingId) {
          updateModel(editingId, savedModel);
        } else {
          addModel(savedModel);
        }
        // Refresh from backend
        const refreshResponse = await fetch('/api/connections/models');
        if (refreshResponse.ok) {
          const modelsData = await refreshResponse.json();
          const normalizedModels = modelsData.map((m: any) => ({
            ...m,
            displayName: m.display_name || m.displayName || m.name,
            modelId: m.model_id || m.modelId,
            apiKey: m.api_key || m.apiKey,
            baseUrl: m.base_url || m.baseUrl,
            isDefault: m.is_default || m.isDefault,
          }));
          setLocalModels(normalizedModels);
        }
        setSuccessMessage('LLM model saved successfully!');
        setTimeout(() => setSuccessMessage(null), 3000);
        resetForm();
      }
    } catch (error) {
      console.error('Failed to save model:', error);
    }
  };

  const handleEdit = (model: LLMModel) => {
    // Convert snake_case from backend to camelCase for form
    setForm({
      provider: model.provider,
      name: model.name,
      displayName: (model as any).display_name || model.displayName || '',
      modelId: (model as any).model_id || model.modelId || '',
      apiKey: (model as any).api_key || model.apiKey || '',
      baseUrl: (model as any).base_url || model.baseUrl || '',
      projectId: (model as any).project_id || (model as any).projectId || '',
      isDefault: (model as any).is_default || model.isDefault || false,
    });
    setEditingId(model.id);
    setIsAdding(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this model?')) return;
    
    try {
      const response = await fetch(`/api/connections/models/${id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        deleteModel(id);
        // Refresh from backend
        const refreshResponse = await fetch('/api/connections/models');
        if (refreshResponse.ok) {
          const modelsData = await refreshResponse.json();
          const normalizedModels = modelsData.map((m: any) => ({
            ...m,
            displayName: m.display_name || m.displayName || m.name,
            modelId: m.model_id || m.modelId,
            apiKey: m.api_key || m.apiKey,
            baseUrl: m.base_url || m.baseUrl,
            isDefault: m.is_default || m.isDefault,
          }));
          setLocalModels(normalizedModels);
        }
      }
    } catch (error) {
      console.error('Failed to delete model:', error);
      deleteModel(id);
    }
  };

  const availableModels = form.provider ? DEFAULT_MODELS[form.provider] || [] : [];
  const providerConfig = form.provider ? PROVIDER_CONFIG[form.provider] : null;
  
  // Filter models based on search
  const filteredModels = useMemo(() => {
    if (!modelSearch) return availableModels;
    const search = modelSearch.toLowerCase();
    return availableModels.filter(m => 
      m.modelId.toLowerCase().includes(search) || 
      m.displayName.toLowerCase().includes(search)
    );
  }, [availableModels, modelSearch]);

  return (
    <div style={{ padding: '1rem' }}>
      {successMessage && (
        <InlineNotification
          kind="success"
          title="Success"
          subtitle={successMessage}
          onClose={() => setSuccessMessage(null)}
          lowContrast
          style={{ marginBottom: '1rem' }}
        />
      )}
      
      {!isAdding ? (
        <>
          <Button kind="primary" renderIcon={Add} onClick={() => setIsAdding(true)}>
            Add LLM Model
          </Button>

          <div style={{ marginTop: '1rem' }}>
            {displayModels.length === 0 ? (
              <p style={{ color: 'var(--cds-text-secondary)' }}>
                No LLM models configured yet.
              </p>
            ) : (
              displayModels.map((model) => (
                <div key={model.id} className="connection-card">
                  <div className="connection-card__header">
                    <span className="connection-card__name">
                      {model.displayName || model.name}
                      {model.isDefault && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--cds-support-info)' }}>(default)</span>}
                    </span>
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      <IconButton kind="ghost" size="sm" label="Edit" onClick={() => handleEdit(model)}>
                        <Edit />
                      </IconButton>
                      <IconButton kind="ghost" size="sm" label="Delete" onClick={() => handleDelete(model.id)}>
                        <TrashCan />
                      </IconButton>
                    </div>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)' }}>
                    {PROVIDERS.find(p => p.id === model.provider)?.name} • {model.modelId}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : (
        <div>
          <h4 style={{ marginBottom: '1rem' }}>{editingId ? 'Edit Model' : 'Add Model'}</h4>
          
          <Select
            id="model-provider"
            labelText="Provider"
            value={form.provider}
            onChange={(e) => {
              const provider = e.target.value as LLMModel['provider'];
              const config = PROVIDER_CONFIG[provider];
              setForm({ 
                ...form, 
                provider, 
                modelId: '',
                baseUrl: config?.baseUrlDefault || '',
              });
              setModelSearch('');
            }}
            style={{ marginBottom: '1rem' }}
          >
            {PROVIDERS.map((p) => (
              <SelectItem key={p.id} value={p.id} text={p.name} />
            ))}
          </Select>

          {/* Searchable Model ComboBox */}
          <ComboBox
            id="model-id"
            titleText="Model"
            placeholder="Search or select a model..."
            items={filteredModels}
            itemToString={(item) => item ? `${item.displayName} (${item.modelId})` : ''}
            selectedItem={availableModels.find(m => m.modelId === form.modelId) || null}
            onChange={({ selectedItem }) => {
              if (selectedItem) {
                setForm({ 
                  ...form, 
                  modelId: selectedItem.modelId, 
                  displayName: selectedItem.displayName 
                });
              }
            }}
            onInputChange={(inputValue) => setModelSearch(inputValue || '')}
            style={{ marginBottom: '1rem' }}
          />
          
          <TextInput
            id="model-display-name"
            labelText="Display Name"
            placeholder="My Model"
            value={form.displayName}
            onChange={(e) => setForm({ ...form, displayName: e.target.value })}
            style={{ marginBottom: '1rem' }}
          />
          
          <TextInput
            id="model-api-key"
            type="password"
            labelText={providerConfig?.apiKeyLabel || 'API Key'}
            placeholder={providerConfig?.apiKeyPlaceholder || 'Enter API key'}
            value={form.apiKey}
            onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
            style={{ marginBottom: '1rem' }}
          />
          
          {/* Watsonx Project ID */}
          {providerConfig?.showProjectId && (
            <TextInput
              id="model-project-id"
              labelText="Watsonx Project ID"
              placeholder="ff280e11-e5e9-..."
              value={form.projectId || ''}
              onChange={(e) => setForm({ ...form, projectId: e.target.value })}
              style={{ marginBottom: '1rem' }}
            />
          )}
          
          {/* Base URL for providers that need it */}
          {providerConfig?.showBaseUrl && (
            <TextInput
              id="model-base-url"
              labelText="Base URL"
              placeholder={providerConfig.baseUrlDefault}
              value={form.baseUrl}
              onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
              style={{ marginBottom: '1rem' }}
            />
          )}
          
          <Toggle
            id="model-default"
            labelText="Set as default model"
            labelA="No"
            labelB="Yes"
            toggled={form.isDefault}
            onToggle={(checked) => setForm({ ...form, isDefault: checked })}
            style={{ marginBottom: '1rem' }}
          />

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button kind="primary" onClick={handleSave} disabled={!form.provider || !form.modelId}>
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
