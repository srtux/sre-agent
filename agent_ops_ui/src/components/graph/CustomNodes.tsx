/* eslint-disable react-refresh/only-export-components */
import { memo } from 'react'
import { Handle, Position, NodeProps } from '@xyflow/react'
import { Brain, Wrench, FileText, AlertTriangle, PlayCircle } from 'lucide-react'
import { ContextNode } from '../../types/graphTypes'

const nodeStyles: Record<string, React.CSSProperties> = {
  base: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid transparent',
    background: '#1E293B',
    color: '#F0F4F8',
    minWidth: '220px',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1)',
    transition: 'all 0.2s ease-in-out',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    fontWeight: 600,
  },
  meta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    color: '#94A3B8',
    fontFamily: "'JetBrains Mono', monospace",
  },
  title: {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  THOUGHT: { borderColor: '#3B82F6', background: 'rgba(30, 41, 59, 0.95)' },
  TOOL_CALL: { borderColor: '#10B981', background: 'rgba(30, 41, 59, 0.95)' },
  OBSERVATION: { borderColor: '#F59E0B', background: 'rgba(30, 41, 59, 0.95)' },
  INCIDENT: { borderColor: '#EF4444', background: 'rgba(30, 41, 59, 0.95)' },
  ACTION: { borderColor: '#8B5CF6', background: 'rgba(30, 41, 59, 0.95)' },
}

const getIcon = (type: string) => {
  switch (type) {
    case 'THOUGHT': return <Brain size={16} color="#3B82F6" />
    case 'TOOL_CALL': return <Wrench size={16} color="#10B981" />
    case 'OBSERVATION': return <FileText size={16} color="#F59E0B" />
    case 'INCIDENT': return <AlertTriangle size={16} color="#EF4444" />
    case 'ACTION': return <PlayCircle size={16} color="#8B5CF6" />
    default: return null
  }
}


const BaseNode = ({ data, selected }: NodeProps) => {
  const customData = data as ContextNode & { _layoutMode?: string }
  const typeStyle = nodeStyles[customData.type] || {}
  const isVertical = customData._layoutMode === 'vertical'

  return (
    <div
      style={{
        ...nodeStyles.base,
        ...typeStyle,
        boxShadow: selected
          ? `0 0 0 2px ${typeStyle.borderColor}, 0 4px 6px -1px rgba(0, 0, 0, 0.2)`
          : nodeStyles.base.boxShadow,
      }}
      title={customData.label}
    >
      <Handle
        type="target"
        position={isVertical ? Position.Top : Position.Left}
        style={{ background: '#94A3B8', width: '8px', height: '8px', border: '2px solid #1E293B' }}
      />
      <div style={nodeStyles.header}>
        {getIcon(customData.type)}
        <span style={nodeStyles.title}>{customData.label}</span>
      </div>
      <div style={nodeStyles.meta}>
        {customData.metadata?.duration != null && <span>{customData.metadata.duration}ms</span>}
        {customData.metadata?.tokenCount != null && <span>{customData.metadata.tokenCount} tokens</span>}
        {!customData.metadata?.duration && !customData.metadata?.tokenCount && <span>{customData.timestamp ? new Date(customData.timestamp).toLocaleTimeString() : ''}</span>}
      </div>
      <Handle
        type="source"
        position={isVertical ? Position.Bottom : Position.Right}
        style={{ background: '#94A3B8', width: '8px', height: '8px', border: '2px solid #1E293B' }}
      />
    </div>
  )
}

export const ThoughtNode = memo(BaseNode)
export const ToolNode = memo(BaseNode)
export const ObservationNode = memo(BaseNode)
export const IncidentNode = memo(BaseNode)
export const ActionNode = memo(BaseNode)

const nodeTypes = {
  THOUGHT: ThoughtNode,
  TOOL_CALL: ToolNode,
  OBSERVATION: ObservationNode,
  INCIDENT: IncidentNode,
  ACTION: ActionNode,
}

export default nodeTypes
