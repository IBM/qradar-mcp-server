import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Chat, Message, QRadarConnection, MCPServer, LLMModel } from '../types';

// Generate unique IDs (works on HTTP, not just HTTPS)
const generateId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

// Chat Store
interface ChatState {
  chats: Chat[];
  activeChatId: string | null;
  
  createChat: () => string;
  deleteChat: (id: string) => void;
  renameChat: (id: string, title: string) => void;
  setActiveChat: (id: string | null) => void;
  addMessage: (chatId: string, message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (chatId: string, messageId: string, updates: Partial<Message>) => void;
  getActiveChat: () => Chat | undefined;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      chats: [],
      activeChatId: null,

      createChat: () => {
        const newChat: Chat = {
          id: generateId(),
          title: 'New Chat',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        set((state) => ({
          chats: [newChat, ...state.chats],
          activeChatId: newChat.id,
        }));
        return newChat.id;
      },

      deleteChat: (id: string) => {
        set((state) => ({
          chats: state.chats.filter((c) => c.id !== id),
          activeChatId: state.activeChatId === id ? null : state.activeChatId,
        }));
      },

      renameChat: (id: string, title: string) => {
        set((state) => ({
          chats: state.chats.map((c) =>
            c.id === id ? { ...c, title, updatedAt: new Date() } : c
          ),
        }));
      },

      setActiveChat: (id: string | null) => {
        set({ activeChatId: id });
      },

      addMessage: (chatId: string, message: Omit<Message, 'id' | 'timestamp'>) => {
        const newMessage: Message = {
          ...message,
          id: generateId(),
          timestamp: new Date(),
        };
        set((state) => ({
          chats: state.chats.map((c) =>
            c.id === chatId
              ? {
                  ...c,
                  messages: [...c.messages, newMessage],
                  updatedAt: new Date(),
                  title: c.messages.length === 0 && message.role === 'user' 
                    ? message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '')
                    : c.title,
                }
              : c
          ),
        }));
      },

      updateMessage: (chatId: string, messageId: string, updates: Partial<Message>) => {
        set((state) => ({
          chats: state.chats.map((c) =>
            c.id === chatId
              ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === messageId ? { ...m, ...updates } : m
                  ),
                  updatedAt: new Date(),
                }
              : c
          ),
        }));
      },

      getActiveChat: () => {
        const state = get();
        return state.chats.find((c) => c.id === state.activeChatId);
      },
    }),
    { name: 'qradar-mcp-chats' }
  )
);

// Connections Store (persisted to localStorage)
interface ConnectionState {
  qradarConnections: QRadarConnection[];
  mcpServers: MCPServer[];
  models: LLMModel[];
  activeQRadarId: string | null;
  activeModelId: string | null;

  addQRadarConnection: (conn: Omit<QRadarConnection, 'id'>) => void;
  updateQRadarConnection: (id: string, updates: Partial<QRadarConnection>) => void;
  deleteQRadarConnection: (id: string) => void;
  setActiveQRadar: (id: string | null) => void;

  addModel: (model: Omit<LLMModel, 'id'>) => void;
  updateModel: (id: string, updates: Partial<LLMModel>) => void;
  deleteModel: (id: string) => void;
  setActiveModel: (id: string | null) => void;

  addMCPServer: (server: Omit<MCPServer, 'id' | 'status'>) => void;
  updateMCPServer: (id: string, updates: Partial<MCPServer>) => void;
  deleteMCPServer: (id: string) => void;

  syncFromBackend: () => Promise<void>;
}

export const useConnectionStore = create<ConnectionState>()(
  persist(
    (set) => ({
      qradarConnections: [],
      mcpServers: [],
      models: [],
      activeQRadarId: null,
      activeModelId: null,

      addQRadarConnection: (conn: Omit<QRadarConnection, 'id'>) => {
        const newConn: QRadarConnection = { ...conn, id: generateId() };
        set((state) => ({
          qradarConnections: [...state.qradarConnections, newConn],
          activeQRadarId: conn.isDefault ? newConn.id : state.activeQRadarId,
        }));
      },

      updateQRadarConnection: (id: string, updates: Partial<QRadarConnection>) => {
        set((state) => ({
          qradarConnections: state.qradarConnections.map((c) =>
            c.id === id ? { ...c, ...updates } : c
          ),
        }));
      },

      deleteQRadarConnection: (id: string) => {
        set((state) => ({
          qradarConnections: state.qradarConnections.filter((c) => c.id !== id),
          activeQRadarId: state.activeQRadarId === id ? null : state.activeQRadarId,
        }));
      },

      setActiveQRadar: (id: string | null) => {
        set({ activeQRadarId: id });
      },

      addModel: (model: Omit<LLMModel, 'id'>) => {
        const newModel: LLMModel = { ...model, id: generateId() };
        set((state) => ({
          models: [...state.models, newModel],
          activeModelId: model.isDefault ? newModel.id : state.activeModelId,
        }));
      },

      updateModel: (id: string, updates: Partial<LLMModel>) => {
        set((state) => ({
          models: state.models.map((m) =>
            m.id === id ? { ...m, ...updates } : m
          ),
        }));
      },

      deleteModel: (id: string) => {
        set((state) => ({
          models: state.models.filter((m) => m.id !== id),
          activeModelId: state.activeModelId === id ? null : state.activeModelId,
        }));
      },

      setActiveModel: (id: string | null) => {
        set({ activeModelId: id });
      },

      addMCPServer: (server: Omit<MCPServer, 'id' | 'status'>) => {
        const newServer: MCPServer = { ...server, id: generateId(), status: 'stopped' };
        set((state) => ({
          mcpServers: [...state.mcpServers, newServer],
        }));
      },

      updateMCPServer: (id: string, updates: Partial<MCPServer>) => {
        set((state) => ({
          mcpServers: state.mcpServers.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        }));
      },

      deleteMCPServer: (id: string) => {
        set((state) => ({
          mcpServers: state.mcpServers.filter((s) => s.id !== id),
        }));
      },

      // Sync all data from backend API
      syncFromBackend: async () => {
        try {
          // Fetch QRadar connections
          const qradarRes = await fetch('/api/connections/qradar');
          if (qradarRes.ok) {
            const qradarData = await qradarRes.json();
            set({ qradarConnections: qradarData });
            // Set active if there's a default
            const defaultQradar = qradarData.find((c: any) => c.is_default || c.isDefault);
            if (defaultQradar) {
              set({ activeQRadarId: defaultQradar.id });
            }
          }

          // Fetch MCP servers
          const mcpRes = await fetch('/api/mcp/servers');
          if (mcpRes.ok) {
            const mcpData = await mcpRes.json();
            set({ mcpServers: mcpData });
          }

          // Fetch LLM models
          const modelsRes = await fetch('/api/connections/models');
          if (modelsRes.ok) {
            const modelsData = await modelsRes.json();
            // Normalize snake_case to camelCase
            const normalizedModels = modelsData.map((m: any) => ({
              ...m,
              displayName: m.display_name || m.displayName || m.name,
              modelId: m.model_id || m.modelId,
              apiKey: m.api_key || m.apiKey,
              baseUrl: m.base_url || m.baseUrl,
              isDefault: m.is_default || m.isDefault,
            }));
            set({ models: normalizedModels });
            // Set active if there's a default
            const defaultModel = normalizedModels.find((m: any) => m.isDefault);
            if (defaultModel) {
              set({ activeModelId: defaultModel.id });
            }
          }
        } catch (error) {
          console.error('Failed to sync from backend:', error);
        }
      },
    }),
    { name: 'qradar-mcp-connections' }
  )
);

// UI Store (non-persisted)
interface UIState {
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  settingsOpen: boolean;
  settingsTab: 'qradar' | 'mcp' | 'models' | 'preferences';
  
  toggleSidebar: () => void;
  toggleRightPanel: () => void;
  openSettings: (tab?: 'qradar' | 'mcp' | 'models' | 'preferences') => void;
  closeSettings: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  rightPanelOpen: false,
  settingsOpen: false,
  settingsTab: 'qradar',

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleRightPanel: () => set((state) => ({ rightPanelOpen: !state.rightPanelOpen })),
  openSettings: (tab = 'qradar') => set({ settingsOpen: true, settingsTab: tab }),
  closeSettings: () => set({ settingsOpen: false }),
}));
