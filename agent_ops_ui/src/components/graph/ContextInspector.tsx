import { X } from 'lucide-react'
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued'
import { useAgentGraph } from '../../hooks/useAgentGraph'
import { ContextNodeProps } from '../../types/graphTypes'

// Mock Data
const mockGraphData: Record<string, ContextNodeProps> = {
  '1': {
    id: '1', type: 'INCIDENT', label: 'Incident Detected: High Latency',
    diff: {
      addedData: { incident_id: "INC-1234", status: "investigating" },
      workingMemory: { incident_id: "INC-1234", status: "investigating" }
    }
  },
  '3': {
    id: '3', type: 'TOOL_CALL', label: 'query_logs(db)',
    diff: {
      addedData: { action: "query_logs", target: "db" },
      workingMemory: { incident_id: "INC-1234", status: "investigating", action: "query_logs", target: "db" }
    }
  },
  '4': {
    id: '4', type: 'OBSERVATION', label: 'DB connection pool exhausted',
    diff: {
      addedData: { db_metrics: { connections: 1000, max: 1000 } },
      workingMemory: { incident_id: "INC-1234", status: "investigating", db_metrics: { connections: 1000, max: 1000 } }
    }
  }
}

interface Props {
  nodeId: string | null
  sessionId?: string | null
  onClose: () => void
}

const customDiffStyles = {
  variables: {
    dark: {
      diffViewerBackground: '#0F172A',
      diffViewerColor: '#94A3B8',
      addedBackground: 'rgba(16, 185, 129, 0.15)',
      addedColor: '#A7F3D0',
      removedBackground: 'rgba(239, 68, 68, 0.15)',
      removedColor: '#FCA5A5',
      wordAddedBackground: 'rgba(16, 185, 129, 0.4)',
      wordRemovedBackground: 'rgba(239, 68, 68, 0.4)',
      addedGutterBackground: 'rgba(16, 185, 129, 0.1)',
      removedGutterBackground: 'rgba(239, 68, 68, 0.1)',
      gutterBackground: '#1E293B',
      gutterBackgroundDark: '#1E293B',
      emptyLineBackground: '#0F172A',
      gutterColor: '#64748B',
      codeFoldGutterBackground: '#1E293B',
      codeFoldBackground: '#1E293B',
    },
  },
  line: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    padding: '4px',
  },
  content: {
    width: '100%',
  },
}

export default function ContextInspector({ nodeId, sessionId, onClose }: Props) {
  const { nodes } = useAgentGraph(sessionId || null)

  if (!nodeId) return null

  const realNode = nodes.find(n => n.id === nodeId)
  const backendData = realNode?.data

  // Synthesize nodeData, preferring real BigQuery payload over mock data
  const nodeData = mockGraphData[nodeId] || {
    id: nodeId,
    type: backendData?.type || 'UNKNOWN',
    label: backendData?.label || `Node ${nodeId}`,
    diff: {
      addedData: backendData?.metadata || { info: "No precise mock data for this node." },
      workingMemory: backendData?.metadata || { info: "No precise mock data for this node." }
    }
  }

  // If the backend has actual diff data embedded in metadata, use it natively
  const metadata = backendData?.metadata as Record<string, unknown> | undefined
  if (metadata?.diff && typeof metadata.diff === 'object') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    nodeData.diff = metadata.diff as any
  } else if (metadata?.workingMemory && typeof metadata.workingMemory === 'object') {
    nodeData.diff = {
      addedData: (metadata.addedData as Record<string, unknown>) || {},
      workingMemory: (metadata.workingMemory as Record<string, unknown>) || {},
    }
  }

  const previousStateObj = { ...nodeData.diff.workingMemory }
  // Subtract added data from current working memory to simulate previous state
  for (const key of Object.keys(nodeData.diff.addedData)) {
    delete previousStateObj[key]
  }

  const oldString = JSON.stringify(previousStateObj, null, 2)
  const newString = JSON.stringify(nodeData.diff.workingMemory, null, 2)

  return (
    <div style={{
      position: 'absolute',
      right: 0,
      top: 0,
      bottom: 0,
      width: '500px',
      background: '#1E293B',
      borderLeft: '1px solid #334155',
      boxShadow: '-4px 0 15px rgba(0, 0, 0, 0.3)',
      zIndex: 10,
      display: 'flex',
      flexDirection: 'column',
      transition: 'transform 0.3s ease-in-out',
      transform: nodeId ? 'translateX(0)' : 'translateX(100%)',
    }}>
      <div style={{
        padding: '16px',
        borderBottom: '1px solid #334155',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: '#0F172A',
      }}>
        <h3 style={{ margin: 0, color: '#F0F4F8', fontSize: '15px', fontWeight: 600 }}>Context State Inspector</h3>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#94A3B8',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
            transition: 'background 0.2s',
          }}
          onMouseOver={(e) => e.currentTarget.style.background = 'rgba(148, 163, 184, 0.1)'}
          onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
        >
          <X size={18} />
        </button>
      </div>

      <div style={{ padding: '16px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h4 style={{ margin: '0 0 8px 0', color: '#CBD5E1', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Node Overview
          </h4>
          <div style={{ background: '#0F172A', padding: '12px', borderRadius: '6px', fontSize: '13px', fontFamily: "'JetBrains Mono', monospace", border: '1px solid #334155' }}>
            <div style={{ color: '#06B6D4', marginBottom: '4px' }}>Type: {nodeData.type}</div>
            <div style={{ color: '#F0F4F8' }}>{nodeData.label}</div>
          </div>
        </div>

        <div>
          <h4 style={{ margin: '0 0 8px 0', color: '#3B82F6', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Working Memory Diff
          </h4>
          <div style={{ border: '1px solid #334155', borderRadius: '6px', overflow: 'hidden' }}>
            <ReactDiffViewer
              oldValue={oldString}
              newValue={newString}
              splitView={false}
              useDarkTheme={true}
              styles={customDiffStyles}
              compareMethod={DiffMethod.WORDS}
              hideLineNumbers={false}
              showDiffOnly={false}
              leftTitle="Previous State"
              rightTitle="Current State"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
