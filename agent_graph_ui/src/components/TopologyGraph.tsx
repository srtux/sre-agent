import { useEffect, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import type { TopologyNode, TopologyEdge } from '../types'

const NODE_WIDTH = 180
const NODE_HEIGHT = 60

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 80, ranksep: 150 })

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  dagre.layout(g)

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id)
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

const nodeColorMap: Record<string, string> = {
  agent: '#26A69A',
  tool: '#FFA726',
  llm: '#AB47BC',
}

const nodeStyles: Record<string, React.CSSProperties> = {
  agent: {
    background: '#26A69A',
    color: '#ffffff',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 600,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px solid #2bbbad',
    boxShadow: '0 2px 8px rgba(38, 166, 154, 0.3)',
  },
  tool: {
    background: '#FFA726',
    color: '#1a1a1a',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 600,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px solid #ffb74d',
    boxShadow: '0 2px 8px rgba(255, 167, 38, 0.3)',
  },
  llm: {
    background: '#AB47BC',
    color: '#ffffff',
    borderRadius: '10px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 600,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px solid #ba68c8',
    boxShadow: '0 2px 8px rgba(171, 71, 188, 0.3)',
  },
}

const subtextStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 400,
  opacity: 0.85,
  marginTop: '2px',
}

const badgeContainerStyle: React.CSSProperties = {
  display: 'inline-flex',
  gap: 4,
  marginTop: '4px',
}

const latencyBadgeStyle: React.CSSProperties = {
  fontSize: 10,
  padding: '1px 6px',
  borderRadius: 8,
  background: 'rgba(255,255,255,0.15)',
  color: '#c9d1d9',
}

const errorBadgeStyle: React.CSSProperties = {
  fontSize: 10,
  padding: '1px 6px',
  borderRadius: 8,
  background: 'rgba(248,81,73,0.2)',
  color: '#f85149',
}

function getErrorStyles(errorCount: number): React.CSSProperties {
  if (errorCount > 0) {
    return {
      border: '2px solid #f85149',
      animation: 'errorPulse 2s ease-in-out infinite',
    }
  }
  return {}
}

function formatLatency(ms: number | undefined): string {
  if (ms === undefined || ms === null) return '0ms'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function MetricBadges({ nodeData }: { nodeData: TopologyNode['data'] }) {
  return (
    <div style={badgeContainerStyle}>
      <span style={latencyBadgeStyle}>
        {formatLatency(nodeData.avgDurationMs)}
      </span>
      {nodeData.errorCount > 0 && (
        <span style={errorBadgeStyle}>
          {nodeData.errorCount} {nodeData.errorCount === 1 ? 'error' : 'errors'}
        </span>
      )}
    </div>
  )
}

function AgentNode({ data }: NodeProps) {
  const nodeData = data as TopologyNode['data']
  const errorOverrides = getErrorStyles(nodeData.errorCount)
  return (
    <div style={{ ...nodeStyles.agent, ...errorOverrides }}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Executions: {nodeData.executionCount}</div>
      <MetricBadges nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function ToolNode({ data }: NodeProps) {
  const nodeData = data as TopologyNode['data']
  const errorOverrides = getErrorStyles(nodeData.errorCount)
  return (
    <div style={{ ...nodeStyles.tool, ...errorOverrides }}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Calls: {nodeData.executionCount}</div>
      <MetricBadges nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function LLMNode({ data }: NodeProps) {
  const nodeData = data as TopologyNode['data']
  const errorOverrides = getErrorStyles(nodeData.errorCount)
  return (
    <div style={{ ...nodeStyles.llm, ...errorOverrides }}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Tokens: {nodeData.totalTokens}</div>
      <MetricBadges nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

const nodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
  llm: LLMNode,
}

function mapNodeType(nodeType: string): string {
  if (nodeType in nodeTypes) return nodeType
  return 'agent'
}

interface TopologyGraphProps {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  onNodeClick?: (nodeId: string) => void
  onEdgeClick?: (sourceId: string, targetId: string) => void
}

export default function TopologyGraph({ nodes, edges, onNodeClick, onEdgeClick }: TopologyGraphProps) {
  // Inject errorPulse keyframe animation into document head
  useEffect(() => {
    const styleEl = document.createElement('style')
    styleEl.textContent = `
      @keyframes errorPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(248, 81, 73, 0.4); }
        50% { box-shadow: 0 0 12px 4px rgba(248, 81, 73, 0.6); }
      }
    `
    document.head.appendChild(styleEl)
    return () => {
      document.head.removeChild(styleEl)
    }
  }, [])

  const toReactFlowNodes = useCallback((): Node[] => {
    return nodes.map((n) => ({
      id: n.id,
      type: mapNodeType(n.data.nodeType),
      data: n.data,
      position: n.position,
    }))
  }, [nodes])

  const toReactFlowEdges = useCallback((): Edge[] => {
    return edges.map((e) => {
      const hasErrors = e.data.errorCount > 0
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        animated: hasErrors,
        style: hasErrors
          ? { stroke: '#f85149', strokeWidth: 2 }
          : { stroke: '#30363d', strokeWidth: 2 },
        label: `${e.data.callCount} calls`,
        labelStyle: { fill: '#8b949e', fontSize: 11 },
        labelBgStyle: { fill: '#0d1117', fillOpacity: 0.8 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      }
    })
  }, [edges])

  const [rfNodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  useEffect(() => {
    const rawNodes = toReactFlowNodes()
    const rawEdges = toReactFlowEdges()
    const { nodes: layouted, edges: layoutedEdges } = getLayoutedElements(
      rawNodes,
      rawEdges,
    )
    setNodes(layouted)
    setEdges(layoutedEdges)
  }, [toReactFlowNodes, toReactFlowEdges, setNodes, setEdges])

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeClick?.(node.id)
    },
    [onNodeClick],
  )

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      // Edge IDs use "source->target" format
      const parts = edge.id.split('->')
      if (parts.length === 2) {
        onEdgeClick?.(parts[0], parts[1])
      }
    },
    [onEdgeClick],
  )

  return (
    <div style={{ flex: 1, minHeight: '500px', background: '#0d1117', borderRadius: '8px' }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#21262d" gap={20} />
        <Controls
          style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '6px' }}
        />
        <MiniMap
          nodeColor={(node) => {
            const nt = (node.data as TopologyNode['data'])?.nodeType ?? 'agent'
            return nodeColorMap[nt] ?? '#8b949e'
          }}
          maskColor="rgba(13, 17, 23, 0.8)"
          style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '6px' }}
        />
      </ReactFlow>
    </div>
  )
}
