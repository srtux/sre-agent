import { useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  Handle,
  Position,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import type { AgentGraphData } from '../../types/sre'
import { colors, typography } from '../../theme/tokens'

const NODE_W = 180
const NODE_H = 60

function layoutGraph(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 120 })

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  edges.forEach((e) => g.setEdge(e.source, e.target))

  dagre.layout(g)

  const layouted = nodes.map((n) => {
    const pos = g.node(n.id)
    return {
      ...n,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
    }
  })

  return { nodes: layouted, edges }
}

const NODE_TYPE_COLORS: Record<string, string> = {
  agent: '#26A69A',
  sub_agent: '#00ACC1',
  tool: '#FFA726',
  llm: '#AB47BC',
  user: '#06B6D4',
}

function AgentGraphNode({ data }: NodeProps) {
  const d = data as Record<string, unknown>
  const nodeType = (d.nodeType as string) ?? 'agent'
  const borderColor = NODE_TYPE_COLORS[nodeType.toLowerCase()] ?? '#334155'
  const errorCount = (d.errorCount as number) ?? 0

  return (
    <div
      style={{
        background: colors.surface,
        border: `2px solid ${errorCount > 0 ? colors.error : borderColor}`,
        borderRadius: 8,
        padding: '6px 10px',
        width: NODE_W,
        height: NODE_H,
        fontFamily: typography.monoFamily,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        boxShadow: errorCount > 0 ? `0 0 8px ${colors.error}40` : '0 2px 8px rgba(0,0,0,0.3)',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ fontSize: 12, fontWeight: 600, color: colors.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {d.label as string}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: colors.textMuted }}>
        <span>x{d.executionCount as number}</span>
        <span>{formatTokens(d.totalTokens as number)}</span>
        {errorCount > 0 && <span style={{ color: colors.error }}>{errorCount} err</span>}
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}

function formatTokens(n?: number): string {
  if (!n) return '0 tok'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M tok`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K tok`
  return `${n} tok`
}

const nodeTypes = { agentGraphNode: AgentGraphNode }

export default function AgentGraph({ data }: { data: AgentGraphData }) {
  const { nodes, edges } = useMemo(() => {
    const rfNodes: Node[] = data.nodes.map((n) => ({
      id: n.id,
      type: 'agentGraphNode',
      data: {
        label: n.label,
        nodeType: n.nodeType,
        executionCount: n.executionCount,
        totalTokens: n.totalTokens,
        errorCount: n.errorCount,
        avgDurationMs: n.avgDurationMs,
      },
      position: { x: 0, y: 0 },
    }))

    const rfEdges: Edge[] = data.edges.map((e, i) => ({
      id: `e-${i}-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      animated: e.errorCount > 0,
      label: `${e.callCount} calls`,
      labelStyle: { fill: colors.textMuted, fontSize: 10, fontFamily: typography.monoFamily },
      labelBgStyle: { fill: colors.background, fillOpacity: 0.8 },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 4,
      style: {
        stroke: e.errorCount > 0 ? colors.error : colors.surfaceBorder,
        strokeWidth: Math.min(1 + e.callCount * 0.3, 4),
      },
    }))

    return layoutGraph(rfNodes, rfEdges)
  }, [data])

  if (!data.nodes.length) {
    return (
      <div style={{ width: '100%', height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: colors.textMuted, background: colors.background }}>
        No graph data
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height: '100%', minHeight: 400, background: colors.background }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Background color="#334155" gap={20} />
        <Controls style={{ background: colors.surface, border: `1px solid ${colors.surfaceBorder}`, borderRadius: 6 }} />
        <MiniMap
          maskColor="rgba(15, 23, 42, 0.8)"
          style={{ background: colors.surface, border: `1px solid ${colors.surfaceBorder}`, borderRadius: 6 }}
        />
      </ReactFlow>
    </div>
  )
}
