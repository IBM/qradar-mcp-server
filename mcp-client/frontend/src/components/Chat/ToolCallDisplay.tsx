import { useState } from 'react';
import { Tag } from '@carbon/react';
import { ChevronDown, ChevronUp, Checkmark, WarningFilled, InProgress } from '@carbon/icons-react';
import type { ToolCall } from '../../types';

interface ToolCallDisplayProps {
  toolCall: ToolCall;
}

export default function ToolCallDisplay({ toolCall }: ToolCallDisplayProps) {
  const [expanded, setExpanded] = useState(false);

  const statusIcon = {
    pending: <InProgress size={16} />,
    success: <Checkmark size={16} />,
    error: <WarningFilled size={16} />,
  };

  const statusColor = {
    pending: 'blue',
    success: 'green',
    error: 'red',
  } as const;

  return (
    <div className="tool-call">
      <div className="tool-call__header" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        <span className="tool-call__name">{toolCall.name}</span>
        <div className="tool-call__status">
          <Tag type={statusColor[toolCall.status]} size="sm">
            {statusIcon[toolCall.status]}
            <span style={{ marginLeft: '0.25rem' }}>{toolCall.status}</span>
          </Tag>
        </div>
      </div>
      
      {expanded && (
        <div className="tool-call__content">
          <strong>Arguments:</strong>
          <pre>{JSON.stringify(toolCall.arguments, null, 2)}</pre>
          
          {toolCall.result && (
            <>
              <strong>Result:</strong>
              <pre>{toolCall.result}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
