import { useEffect, useCallback, useMemo, useState } from 'react'
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
  Panel,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import type { TopologyNode, TopologyEdge, ViewMode, TimeSeriesData, TimeSeriesPoint } from '../types'
import Sparkline, { SPARK_H, extractSparkSeries, sparkColor } from './Sparkline'
import { GraphTopologyHelper } from '../utils/topology'
import BackEdge from './BackEdge'

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

  // Only layout DAG edges
  edges.forEach((edge) => {
    if (edge.type !== 'back') {
      g.setEdge(edge.source, edge.target)
    }
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

const nodeStyles: Record<string, React.CSSProperties> = {
  user: {
    background: '#1A2744',
    color: '#ffffff',
    borderRadius: '50%',
    padding: '10px',
    fontSize: '11px',
    fontWeight: 600,
    width: 80,
    height: 80,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px solid #58a6ff',
    boxShadow: '0 2px 12px rgba(88, 166, 255, 0.2)',
  },
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
    position: 'relative',
  },
  sub_agent: {
    background: '#00838F', // Darker Teal for sub-agents
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
    border: '2px solid #00ACC1',
    boxShadow: '0 2px 8px rgba(0, 172, 193, 0.3)',
    position: 'relative',
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
    position: 'relative',
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
    position: 'relative',
  },
}

const BaseNodeStyle = (nodeData: NodeDataExtended, baseStyle: React.CSSProperties) => {
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
  return {
    ...baseStyle,
    ...errorOverrides,
    ...heatOverrides,
    opacity: nodeData._isDimmed ? 0.2 : 1.0,
    transition: 'opacity 0.3s ease, background 0.3s ease, border 0.3s ease, width 0.3s ease, height 0.3s ease',
  }
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

function heatmapColor(t: number): string {
  const v = Math.max(0, Math.min(1, t))
  if (v < 0.5) {
    const sub = v * 2
    const r = 255
    const g = Math.round(255 - sub * (255 - 204))
    const b = Math.round(255 - sub * 255)
    return `rgb(${r},${g},${b})`
  }
  const sub = (v - 0.5) * 2
  const r = Math.round(255 - sub * (255 - 204))
  const g = Math.round(204 - sub * 204)
  const b = 0
  return `rgb(${r},${g},${b})`
}

function getMaxMetric(nodes: TopologyNode[], key: 'totalTokens' | 'avgDurationMs'): number {
  let max = 0
  for (const n of nodes) {
    const val = n.data[key]
    if (typeof val === 'number' && val > max) max = val
  }
  return max || 1
}

function getScaledDimensions(t: number): { width: number; height: number } {
  const scale = 1 + t * 0.6
  const scaledW = Math.round(NODE_WIDTH * scale)
  const scaledH = Math.round(NODE_HEIGHT * scale)
  return { width: scaledW, height: scaledH }
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
  _isDimmed?: boolean
  _expanded?: boolean
  _hasChildren?: boolean
  _childrenCount?: number
  _onToggleExpand?: () => void
}

function NodeSparkline({ nodeData }: { nodeData: NodeDataExtended }) {
  if (!nodeData._sparklinePoints || nodeData._sparklinePoints.length < 2) return null
  const vm = nodeData._viewMode ?? 'topology'
  const series = extractSparkSeries(nodeData._sparklinePoints, vm)
  return <Sparkline points={series} color={sparkColor(vm)} />
}

function ExpandButton({ nodeData }: { nodeData: NodeDataExtended }) {
  if (!nodeData._hasChildren) return null;
  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
        nodeData._onToggleExpand?.();
      }}
      style={{
        position: 'absolute',
        bottom: -12,
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: 12,
        padding: '2px 8px',
        fontSize: 10,
        color: '#c9d1d9',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        zIndex: 10,
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
      }}
    >
      {nodeData._expanded ? '🔽 Collapse' : `▶ Expand (${nodeData._childrenCount})`}
    </div>
  )
}

function UserNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  return (
    <div style={BaseNodeStyle(nodeData, nodeStyles.user)}>
      <div style={{ fontSize: 24, marginBottom: 4 }}>👤</div>
      <div>User</div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function AgentNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const isSubAgent = nodeData.nodeType?.toLowerCase() === 'sub_agent'
  return (
    <div style={BaseNodeStyle(nodeData, isSubAgent ? nodeStyles.sub_agent : nodeStyles.agent)}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Executions: {nodeData.executionCount}</div>
      <MetricBadges nodeData={nodeData} />
      <NodeSparkline nodeData={nodeData} />
      <ExpandButton nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function ToolNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  return (
    <div style={BaseNodeStyle(nodeData, nodeStyles.tool)}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Calls: {nodeData.executionCount}</div>
      <MetricBadges nodeData={nodeData} />
      <NodeSparkline nodeData={nodeData} />
      <ExpandButton nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function LLMNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  return (
    <div style={BaseNodeStyle(nodeData, nodeStyles.llm)}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Tokens: {nodeData.totalTokens}</div>
      <MetricBadges nodeData={nodeData} />
      <NodeSparkline nodeData={nodeData} />
      <ExpandButton nodeData={nodeData} />
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

const nodeTypes = {
  agent: AgentNode,
  sub_agent: AgentNode,
  tool: ToolNode,
  llm: LLMNode,
  user: UserNode,
}

const edgeTypes = {
  back: BackEdge,
}

function mapNodeType(nodeType: string, label: string): string {
  const lower = nodeType?.toLowerCase() || ''
  if (lower === 'user' || label.toLowerCase() === 'user') return 'user'
  if (lower === 'sub_agent') return 'sub_agent'
  if (lower in nodeTypes) return lower
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
  selectedNodeId?: string | null
}

export default function TopologyGraph({
  nodes,
  edges,
  viewMode = 'topology',
  sparklineData,
  onNodeClick,
  onEdgeClick,
  selectedNodeId
}: TopologyGraphProps) {

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [highlightedPath, setHighlightedPath] = useState<Set<string>>(new Set())

  const topology = useMemo(() => {
    return GraphTopologyHelper.analyze(nodes, edges)
  }, [nodes, edges])

  // Initial expand
  useEffect(() => {
    const initial = new Set<string>()
    if (nodes.length <= 25) {
      nodes.forEach(n => {
        if (topology.hasChildren(n.id)) initial.add(n.id)
      })
    } else {
      topology.rootIds.forEach(id => initial.add(id))
    }
    setExpandedIds(initial)
  }, [topology, nodes])

  // Re-compute highlighted path when selected node changes
  useEffect(() => {
    if (selectedNodeId) {
      setHighlightedPath(topology.computePath(selectedNodeId))
    } else {
      setHighlightedPath(new Set())
    }
  }, [selectedNodeId, topology])

  useEffect(() => {
    const styleEl = document.createElement('style')
    styleEl.textContent = `
      @keyframes errorPulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(248, 81, 73, 0.4); }
        50% { box-shadow: 0 0 12px 4px rgba(248, 81, 73, 0.6); }
      }
      @keyframes marchingAnts {
        from { stroke-dashoffset: 20; }
        to { stroke-dashoffset: 0; }
      }
      .react-flow__edge.back-edge path.react-flow__edge-path {
        stroke-dasharray: 10 5;
        animation: marchingAnts 1s linear infinite;
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

    const visibleGraph = topology.getVisibleGraph(expandedIds)

    return visibleGraph.nodes.map((n) => {
      let heatColor: string | undefined
      let scaledWidth: number | undefined
      let scaledHeight: number | undefined

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

      let sparkPoints: TimeSeriesPoint[] | undefined
      if (sparklineData?.series[n.id] && sparklineData.series[n.id].length >= 2) {
        sparkPoints = sparklineData.series[n.id]
        if (scaledHeight) scaledHeight += SPARK_H + 4
        else scaledHeight = NODE_HEIGHT + SPARK_H + 4
      }

      const isDimmed = selectedNodeId != null && !highlightedPath.has(n.id)

      return {
        id: n.id,
        type: mapNodeType(n.data.nodeType, n.data.label),
        data: {
          ...n.data,
          _heatColor: heatColor,
          _scaledWidth: scaledWidth,
          _scaledHeight: scaledHeight,
          _sparklinePoints: sparkPoints,
          _viewMode: viewMode,
          _isDimmed: isDimmed,
          _expanded: expandedIds.has(n.id),
          _hasChildren: topology.hasChildren(n.id),
          _childrenCount: topology.getChildrenCount(n.id),
          _onToggleExpand: () => {
            setExpandedIds(prev => {
              const next = new Set(prev)
              if (next.has(n.id)) {
                // Collapse logic: also optionally collapse children, but simple toggle for now
                next.delete(n.id)
              } else {
                next.add(n.id)
              }
              return next
            })
          }
        },
        position: n.position,
      }
    })
  }, [nodes, viewMode, sparklineData, expandedIds, topology, selectedNodeId, highlightedPath])

  const toReactFlowEdges = useCallback((): Edge[] => {
    const visibleGraph = topology.getVisibleGraph(expandedIds)
    const allVisibleEdges = [...visibleGraph.dagEdges, ...visibleGraph.backEdges]

    let maxCalls = 1
    for (const e of allVisibleEdges) {
      if (e.data.callCount > maxCalls) maxCalls = e.data.callCount
    }

    return allVisibleEdges.map((e) => {
      const hasErrors = e.data.errorCount > 0
      const isBackEdge = topology.backEdgePairs.has(`${e.source}->${e.target}`)

      const isDimmed = selectedNodeId != null && (!highlightedPath.has(e.source) || !highlightedPath.has(e.target))

      const rawThickness = e.data.callCount / maxCalls
      const strokeWidth = 1.5 + (rawThickness * 3) // Scale from 1.5px to 4.5px

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: isBackEdge ? 'back' : 'default',
        animated: hasErrors,
        className: isBackEdge ? 'back-edge' : '',
        style: {
          stroke: hasErrors ? '#f85149' : (isBackEdge ? '#2bbbad' : '#30363d'),
          strokeWidth,
          opacity: isDimmed ? 0.2 : 1.0,
          transition: 'opacity 0.3s ease',
        },
        label: `${e.data.callCount} calls`,
        labelStyle: { fill: '#8b949e', fontSize: 11, opacity: isDimmed ? 0.2 : 1.0 },
        labelBgStyle: { fill: '#0d1117', fillOpacity: isDimmed ? 0.2 : 0.8 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      }
    })
  }, [expandedIds, topology, selectedNodeId, highlightedPath])

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
      // Toggle selection logic handles in App or here?
      // Handled in App via onNodeClick. App will set selected null if clicked again maybe?
      onNodeClick?.(node.id)
    },
    [onNodeClick],
  )

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
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
        edgeTypes={edgeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#21262d" gap={20} />
        <Controls
          style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '6px' }}
        />
        <MiniMap
          nodeColor={(node) => {
            const nt = (node.data as NodeDataExtended)?.nodeType ?? 'agent'
            if (nt.toLowerCase() === 'user') return '#1A2744'
            if (nt.toLowerCase() === 'sub_agent') return '#00838F'
            if (nt.toLowerCase() === 'agent') return '#26A69A'
            if (nt.toLowerCase() === 'tool') return '#FFA726'
            if (nt.toLowerCase() === 'llm') return '#AB47BC'
            return '#8b949e'
          }}
          maskColor="rgba(13, 17, 23, 0.8)"
          style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '6px' }}
        />
        <Panel position="bottom-center" style={{ marginBottom: 40, display: 'flex', gap: 8 }}>
          <button
            onClick={() => {
              const allIds = new Set(nodes.map(n => n.id))
              setExpandedIds(allIds)
            }}
            style={{
              background: '#21262d', border: '1px solid #30363d', color: '#c9d1d9',
              padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer'
            }}
          >
            Expand All
          </button>
          <button
            onClick={() => {
              const rootIds = new Set(topology.rootIds)
              setExpandedIds(rootIds)
            }}
            style={{
              background: '#21262d', border: '1px solid #30363d', color: '#c9d1d9',
              padding: '4px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer'
            }}
          >
            Collapse Sub-Agents
          </button>
        </Panel>
      </ReactFlow>
      <HeatmapLegend mode={viewMode} />
    </div>
  )
}
