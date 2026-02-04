import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from '../../types';
import ToolCallDisplay from './ToolCallDisplay';

interface MessageBubbleProps {
  message: Message;
}

// Clean up messy LLM output (remove repeated attempts, thinking text)
function cleanLLMResponse(content: string): string {
  // Remove text before the final answer (look for "assistantfinal" marker)
  const finalMarker = content.lastIndexOf('assistantfinal');
  if (finalMarker !== -1) {
    content = content.substring(finalMarker + 'assistantfinal'.length);
  }
  
  // Remove "assistant" markers (but not the word "assistant" in normal text)
  content = content.replace(/\bassistant(analysis|final|thinking)\b/gi, '');
  
  // Remove multiple consecutive newlines
  content = content.replace(/\n{3,}/g, '\n\n');
  
  // Trim whitespace
  content = content.trim();
  
  return content;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  // Clean assistant messages
  const displayContent = message.role === 'assistant' 
    ? cleanLLMResponse(message.content)
    : message.content;

  return (
    <div className={`message ${message.role}`}>
      <div className="message__content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ node, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              const isInline = !match && !String(children).includes('\n');
              
              return isInline ? (
                <code className={className} {...props}>
                  {children}
                </code>
              ) : (
                <SyntaxHighlighter
                  style={oneDark as Record<string, React.CSSProperties>}
                  language={match ? match[1] : 'text'}
                  PreTag="div"
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              );
            },
            // Style tables
            table({ children }) {
              return (
                <div style={{ overflowX: 'auto', marginBottom: '1rem' }}>
                  <table style={{ 
                    borderCollapse: 'collapse', 
                    width: '100%',
                    fontSize: '0.875rem'
                  }}>
                    {children}
                  </table>
                </div>
              );
            },
            th({ children }) {
              return (
                <th style={{ 
                  border: '1px solid var(--cds-border-subtle-01)',
                  padding: '0.5rem',
                  backgroundColor: 'var(--cds-layer-02)',
                  textAlign: 'left',
                  fontWeight: 600
                }}>
                  {children}
                </th>
              );
            },
            td({ children }) {
              return (
                <td style={{ 
                  border: '1px solid var(--cds-border-subtle-01)',
                  padding: '0.5rem'
                }}>
                  {children}
                </td>
              );
            },
          }}
        >
          {displayContent}
        </ReactMarkdown>
      </div>
      
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="message__tools">
          {message.toolCalls.map((tool) => (
            <ToolCallDisplay key={tool.id} toolCall={tool} />
          ))}
        </div>
      )}
    </div>
  );
}
