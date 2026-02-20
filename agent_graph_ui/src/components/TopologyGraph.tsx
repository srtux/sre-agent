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
import type { TopologyNode, TopologyEdge, ViewMode, TimeSeriesData, TimeSeriesPoint } from '../types'
import Sparkline, { SPARK_H, extractSparkSeries, sparkColor } from './Sparkline'

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
    const d = node.data as Record<string, unknown>
    const w = (d._scaledWidth as number) ?? NODE_WIDTH
    const h = (d._scaledHeight as number) ?? NODE_HEIGHT
    g.setNode(node.id, { width: w, height: h })
  })

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  dagre.layout(g)

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id)
    const d = node.data as Record<string, unknown>
    const w = (d._scaledWidth as number) ?? NODE_WIDTH
    const h = (d._scaledHeight as number) ?? NODE_HEIGHT
    return {
      ...node,
      position: {
        x: pos.x - w / 2,
        y: pos.y - h / 2,
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

/** Interpolate between white and deep red based on a 0-1 value. */
function heatmapColor(t: number): string {
  // Clamp to [0, 1]
  const v = Math.max(0, Math.min(1, t))
  // White (#ffffff) -> Yellow (#ffcc00) -> Deep Red (#cc0000)
  if (v < 0.5) {
    const sub = v * 2 // 0-1 within first half
    const r = 255
    const g = Math.round(255 - sub * (255 - 204))
    const b = Math.round(255 - sub * 255)
    return `rgb(${r},${g},${b})`
  }
  const sub = (v - 0.5) * 2 // 0-1 within second half
  const r = Math.round(255 - sub * (255 - 204))
  const g = Math.round(204 - sub * 204)
  const b = 0
  return `rgb(${r},${g},${b})`
}

/** Compute the maximum value for a metric across all nodes. */
function getMaxMetric(nodes: TopologyNode[], key: 'totalTokens' | 'avgDurationMs'): number {
  let max = 0
  for (const n of nodes) {
    const val = n.data[key]
    if (typeof val === 'number' && val > max) max = val
  }
  return max || 1 // avoid division by zero
}

/** Scale a node's dimensions based on its normalized metric value. */
function getScaledDimensions(t: number): { width: number; height: number } {
  const scale = 1 + t * 0.6 // 1x to 1.6x
  return {
    width: Math.round(NODE_WIDTH * scale),
    height: Math.round(NODE_HEIGHT * scale),
  }
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

type NodeDataExtended = TopologyNode['data'] & {
  _heatColor?: string
  _scaledWidth?: number
  _scaledHeight?: number
  _sparklinePoints?: TimeSeriesPoint[]
  _viewMode?: ViewMode
}

function NodeSparkline({ nodeData }: { nodeData: NodeDataExtended }) {
  if (!nodeData._sparklinePoints || nodeData._sparklinePoints.length < 2) return null
  const vm = nodeData._viewMode ?? 'topology'
  const series = extractSparkSeries(nodeData._sparklinePoints, vm)
  return <Sparkline points={series} color={sparkColor(vm)} />
}

function AgentNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const errorOverrides = getErrorStyles(nodeData.errorCount)
  const heatOverrides: React.CSSProperties = nodeData._heatColor
    ? {
      background: nodeData._heatColor,
      border: `2px solid ${nodeData._heatColor}`,
      boxShadow: `0 2px 8px ${nodeData._heatColor}40`,
      width: nodeData._scaledWidth ?? NODE_WIDTH,
      height: nodeData._scaledHeight ?? NODE_HEIGHT,
      color: '#1a1a1a',
    }
    : {}
  return (
    <div style={{ ...nodeStyles.agent, ...errorOverrides, ...heatOverrides }}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Executions: {nodeData.executionCount}</div>
      <MetricBadges nodeData={nodeData} />
      <NodeSparkline nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function ToolNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const errorOverrides = getErrorStyles(nodeData.errorCount)
  const heatOverrides: React.CSSProperties = nodeData._heatColor
    ? {
      background: nodeData._heatColor,
      border: `2px solid ${nodeData._heatColor}`,
      boxShadow: `0 2px 8px ${nodeData._heatColor}40`,
      width: nodeData._scaledWidth ?? NODE_WIDTH,
      height: nodeData._scaledHeight ?? NODE_HEIGHT,
      color: '#1a1a1a',
    }
    : {}
  return (
    <div style={{ ...nodeStyles.tool, ...errorOverrides, ...heatOverrides }}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Calls: {nodeData.executionCount}</div>
      <MetricBadges nodeData={nodeData} />
      <NodeSparkline nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function LLMNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const errorOverrides = getErrorStyles(nodeData.errorCount)
  const heatOverrides: React.CSSProperties = nodeData._heatColor
    ? {
      background: nodeData._heatColor,
      border: `2px solid ${nodeData._heatColor}`,
      boxShadow: `0 2px 8px ${nodeData._heatColor}40`,
      width: nodeData._scaledWidth ?? NODE_WIDTH,
      height: nodeData._scaledHeight ?? NODE_HEIGHT,
      color: '#1a1a1a',
    }
    : {}
  return (
    <div style={{ ...nodeStyles.llm, ...errorOverrides, ...heatOverrides }}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Tokens: {nodeData.totalTokens}</div>
      <MetricBadges nodeData={nodeData} />
      <NodeSparkline nodeData={nodeData} />
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

function HeatmapLegend({ mode }: { mode: ViewMode }) {
  if (mode === 'topology') return null

  const label = mode === 'cost' ? 'Token Cost' : 'Avg Latency'
  const lowLabel = mode === 'cost' ? 'Low' : '0ms'
  const highLabel = mode === 'cost' ? 'High' : 'High ms'

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '10px 14px',
        zIndex: 10,
        fontSize: '12px',
        color: '#c9d1d9',
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: '6px' }}>{label} Heatmap</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ color: '#8b949e' }}>{lowLabel}</span>
        <div
          style={{
            width: '120px',
            height: '12px',
            borderRadius: '6px',
            background: 'linear-gradient(to right, #ffffff, #ffcc00, #cc0000)',
          }}
        />
        <span style={{ color: '#8b949e' }}>{highLabel}</span>
      </div>
    </div>
  )
}

interface TopologyGraphProps {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  viewMode?: ViewMode
  sparklineData?: TimeSeriesData | null
  onNodeClick?: (nodeId: string) => void
  onEdgeClick?: (sourceId: string, targetId: string) => void
}

export default function TopologyGraph({ nodes, edges, viewMode = 'topology', sparklineData, onNodeClick, onEdgeClick }: TopologyGraphProps) {
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
    const maxTokens = getMaxMetric(nodes, 'totalTokens')
    const maxLatency = getMaxMetric(nodes, 'avgDurationMs')

    return nodes.map((n) => {
      let heatColor: string | undefined
      let scaledWidth = NODE_WIDTH
      let scaledHeight = NODE_HEIGHT

      if (viewMode === 'cost') {
        const tokens = n.data.totalTokens ?? 0
        const t = tokens / maxTokens
        heatColor = heatmapColor(t)
        const dims = getScaledDimensions(t)
        scaledWidth = dims.width
        scaledHeight = dims.height
      } else if (viewMode === 'latency') {
        const lat = n.data.avgDurationMs ?? 0
        const t = lat / maxLatency
        heatColor = heatmapColor(t)
        const dims = getScaledDimensions(t)
        scaledWidth = dims.width
        scaledHeight = dims.height
      }

      // Inject sparkline data if available
      let sparkPoints: TimeSeriesPoint[] | undefined
      if (sparklineData?.series[n.id] && sparklineData.series[n.id].length >= 2) {
        sparkPoints = sparklineData.series[n.id]
        scaledHeight += SPARK_H + 4
      }

      return {
        id: n.id,
        type: mapNodeType(n.data.nodeType),
        data: {
          ...n.data,
          _heatColor: heatColor,
          _scaledWidth: scaledWidth,
          _scaledHeight: scaledHeight,
          _sparklinePoints: sparkPoints,
          _viewMode: viewMode,
        },
        position: n.position,
      }
    })
  }, [nodes, viewMode, sparklineData])

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
    <div style={{ width: '100vw', height: '100vh', paddingBottom: '100px', background: '#0d1117', position: 'relative' }}>
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
      <HeatmapLegend mode={viewMode} />
    </div>
  )
}
