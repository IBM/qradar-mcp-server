import { useState, useRef, useEffect } from 'react';
import { TextArea, IconButton } from '@carbon/react';
import { Send, StopFilled, Microphone } from '@carbon/icons-react';
import { useChatStore } from '../../store';
import MessageBubble from './MessageBubble';
import EmptyState from './EmptyState';

export default function ChatContainer() {
  const { chats, activeChatId, createChat, addMessage } = useChatStore();
  
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingStatus, setStreamingStatus] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeChat = chats.find((c) => c.id === activeChatId);

  // Auto-scroll to bottom when new messages arrive or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeChat?.messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput('');

    // Create new chat if none active
    let chatId = activeChatId;
    if (!chatId) {
      chatId = createChat();
    }

    // Add user message
    addMessage(chatId, { role: 'user', content: message });

    // Send to backend API with streaming
    setIsLoading(true);
    setStreamingContent('');
    setStreamingStatus('Connecting...');
    
    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message,
          chat_id: chatId 
        }),
      });
      
      if (!response.ok) {
        throw new Error('HTTP error! status: ' + response.status);
      }
      
      if (!response.body) {
        // Fallback to non-streaming
        const data = await response.json();
        addMessage(chatId, {
          role: 'assistant',
          content: data.message?.content || 'No response',
        });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalContent = '';
      let toolsUsed: string[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'status') {
                setStreamingStatus(data.message);
              } else if (data.type === 'tool_call') {
                toolsUsed.push(data.tool);
                setStreamingStatus('Calling ' + data.tool + '...');
              } else if (data.type === 'tool_result') {
                setStreamingStatus(data.tool + ' completed');
              } else if (data.type === 'content_delta') {
                finalContent += data.delta;
                setStreamingContent(finalContent);
                setStreamingStatus('');
              } else if (data.type === 'content' || data.type === 'content_final') {
                finalContent = data.content;
                setStreamingContent(finalContent);
                setStreamingStatus('');
              } else if (data.type === 'tools_summary') {
                // Tools summary - ignore, don't display
              } else if (data.type === 'error') {
                finalContent = data.content;
                setStreamingContent(finalContent);
                setStreamingStatus('');
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      // Add final message to chat
      if (finalContent) {
        addMessage(chatId, {
          role: 'assistant',
          content: finalContent,
        });
      } else {
        // No content received - add error message
        addMessage(chatId, {
          role: 'assistant',
          content: 'No response received from server.',
        });
      }
      
    } catch (error) {
      console.error('Chat error:', error);
      const errorChatId = activeChatId || chatId;
      if (errorChatId) {
        addMessage(errorChatId, {
          role: 'assistant',
          content: 'Error: ' + (error instanceof Error ? error.message : 'Failed to connect to backend'),
        });
      }
    } finally {
      setIsLoading(false);
      setStreamingContent('');
      setStreamingStatus('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const handleVoiceInput = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      return; // Silently fail on unsupported browsers
    }

    if (isListening) {
      // Stop listening
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    // Start listening - let browser show native permission prompt
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(prev => prev ? `${prev} ${transcript}` : transcript);
      setIsListening(false);
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
      // Let browser handle permission errors naturally - no alerts
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  return (
    <div className="chat-container">
      {!activeChat || activeChat.messages.length === 0 ? (
        <EmptyState onNewChat={() => textareaRef.current?.focus()} />
      ) : (
        <div className="chat-messages">
          {activeChat.messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          
          {/* Streaming content */}
          {isLoading && (
            <>
              {streamingStatus && !streamingContent && (
                <div className="streaming-status">
                  <span className="streaming-status__dot"></span>
                  {streamingStatus}
                </div>
              )}
              {streamingContent && (
                <MessageBubble 
                  message={{ 
                    id: 'streaming', 
                    role: 'assistant', 
                    content: streamingContent,
                    timestamp: new Date()
                  }} 
                />
              )}
            </>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      )}

      <div className="chat-input">
        <div className="chat-input__wrapper">
          <TextArea
            ref={textareaRef}
            id="chat-input"
            labelText=""
            hideLabel
            placeholder="Ask about your QRadar environment..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            className="chat-input__textarea"
            disabled={isLoading}
          />
          <div className="chat-input__actions">
            <IconButton
              kind={isListening ? "primary" : "ghost"}
              size="lg"
              label={isListening ? "Stop listening" : "Voice input"}
              onClick={handleVoiceInput}
              title={isListening ? "Click to stop" : "Click to speak"}
              className={isListening ? "pulse-animation" : ""}
            >
              <Microphone />
            </IconButton>
            <IconButton
              kind="primary"
              size="lg"
              label={isLoading ? 'Stop' : 'Send'}
              onClick={isLoading ? () => setIsLoading(false) : handleSend}
              disabled={!input.trim() && !isLoading}
              className="chat-input__button"
            >
              {isLoading ? <StopFilled /> : <Send />}
            </IconButton>
          </div>
        </div>
      </div>
    </div>
  );
}
