// Chat types
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  status: 'pending' | 'success' | 'error';
}

export interface Chat {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  qradarConnectionId?: string;
  modelId?: string;
}

// Connection types
export interface QRadarConnection {
  id: string;
  name: string;
  url: string;
  token: string;
  verify: boolean;
  isDefault: boolean;
  status?: 'connected' | 'disconnected' | 'error';
}

export interface MCPServer {
  id: string;
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  qradarConnectionId: string;
  status: 'running' | 'stopped' | 'error';
  tools?: MCPTool[];
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

// LLM types
export interface LLMModel {
  id: string;
  provider: 'watsonx' | 'openrouter' | 'openai' | 'anthropic' | 'ollama';
  name: string;
  displayName: string;
  apiKey?: string;
  baseUrl?: string;
  projectId?: string;  // For Watsonx
  modelId: string;
  isDefault: boolean;
}

// API types
export interface ChatRequest {
  message: string;
  chatId?: string;
  qradarConnectionId?: string;
  modelId?: string;
}

export interface ChatResponse {
  chatId: string;
  message: Message;
}

export interface StreamChunk {
  type: 'content' | 'tool_call' | 'tool_result' | 'done' | 'error';
  content?: string;
  toolCall?: ToolCall;
  error?: string;
}
