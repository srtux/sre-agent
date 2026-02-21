import { useEffect, useCallback, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  ControlButton,
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
import type { TopologyNode, TopologyEdge, TimeSeriesData, TimeSeriesPoint } from '../types'
import Sparkline, { SPARK_H, extractSparkSeries, sparkColor } from './Sparkline'
import { GraphTopologyHelper } from '../utils/topology'
import BackEdge from './BackEdge'
import {
  User,
  Bot,
  Wrench,
  Sparkles,
  Activity,
  AlertCircle,
  FileDigit,
  UnfoldHorizontal,
  FoldHorizontal,
  LayoutTemplate,
  Network,
  Plus,
  Minus
} from 'lucide-react'

export type LayoutMode = 'horizontal' | 'vertical' | 'cluster'

const NODE_WIDTH = 200
const NODE_HEIGHT = 64

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  layoutMode: LayoutMode
): { nodes: Node[]; edges: Edge[] } {
  const isCluster = layoutMode === 'cluster'
  const g = new dagre.graphlib.Graph({ compound: isCluster })
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: layoutMode === 'vertical' ? 'TB' : 'LR', nodesep: 80, ranksep: 150 })

  const types = new Set<string>()
  if (isCluster) {
    nodes.forEach(n => {
      const t = String(n.type)
      types.add(t)
    })
    types.forEach(t => {
      g.setNode('group_' + t, { label: t, clusterLabelPos: 'top' })
    })
  }

  nodes.forEach((node) => {
    const d = node.data as Record<string, unknown>
    const w = (d._scaledWidth as number) ?? NODE_WIDTH
    const h = (d._scaledHeight as number) ?? NODE_HEIGHT
    g.setNode(node.id, { width: w, height: h })
    if (isCluster) {
      g.setParent(node.id, 'group_' + String(node.type))
    }
  })

  // Only layout DAG edges
  edges.forEach((edge) => {
    if (edge.type !== 'back') {
      g.setEdge(edge.source, edge.target)
    }
  })

  dagre.layout(g)

  const layoutedNodes: Node[] = []

  if (isCluster) {
    types.forEach(t => {
      const pNode = g.node('group_' + t)
      if (pNode) {
        layoutedNodes.push({
          id: 'group_' + t,
          type: 'group',
          data: { label: t },
          position: { x: pNode.x - pNode.width / 2, y: pNode.y - pNode.height / 2 },
          style: {
            width: pNode.width,
            height: pNode.height,
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '2px dashed rgba(255,255,255,0.1)',
            borderRadius: '16px',
            zIndex: -1
          }
        })
      }
    })
  }

  nodes.forEach((node) => {
    const pos = g.node(node.id)
    const d = node.data as Record<string, unknown>
    const w = (d._scaledWidth as number) ?? NODE_WIDTH
    const h = (d._scaledHeight as number) ?? NODE_HEIGHT

    let x = pos.x - w / 2
    let y = pos.y - h / 2

    if (isCluster) {
      const pNode = g.node('group_' + String(node.type))
      if (pNode) {
        node.parentId = 'group_' + String(node.type)
        x = x - (pNode.x - pNode.width / 2)
        y = y - (pNode.y - pNode.height / 2)
      }
    }

    layoutedNodes.push({
      ...node,
      position: { x, y },
    })
  })

  return { nodes: layoutedNodes, edges }
}

const nodeStyles: Record<string, React.CSSProperties> = {
  user: {
    background: '#1A2744',
    color: '#F0F4F8',
    fontFamily: "'JetBrains Mono', monospace",
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: 600,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    border: '1px solid #06B6D4',
    boxShadow: '0 4px 12px rgba(6, 182, 212, 0.1)',
    position: 'relative',
  },
  agent: {
    background: '#1E293B',
    color: '#F0F4F8',
    fontFamily: "'JetBrains Mono', monospace",
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: 600,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    border: '1px solid #26A69A',
    borderLeftWidth: '4px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
    position: 'relative',
  },
  sub_agent: {
    background: '#1E293B',
    color: '#F0F4F8',
    fontFamily: "'JetBrains Mono', monospace",
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: 600,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    border: '1px solid #00ACC1',
    borderLeftWidth: '4px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
    position: 'relative',
  },
  tool: {
    background: '#1E293B',
    color: '#F0F4F8',
    fontFamily: "'JetBrains Mono', monospace",
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: 600,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    border: '1px solid #FFA726',
    borderLeftWidth: '4px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
    position: 'relative',
  },
  llm: {
    background: '#1E293B',
    color: '#F0F4F8',
    fontFamily: "'JetBrains Mono', monospace",
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: 600,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    border: '1px solid #AB47BC',
    borderLeftWidth: '4px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
    position: 'relative',
  },
}

const BaseNodeStyle = (nodeData: NodeDataExtended, baseStyle: React.CSSProperties) => {
  const errorOverrides = getErrorStyles(nodeData.errorCount)

  let boxOverrides = {}
  if (nodeData._isHighCost && nodeData._isHighLatency) {
    boxOverrides = {
      boxShadow: '0 0 16px 4px rgba(255, 167, 38, 0.4), 0 0 16px 4px rgba(204, 0, 0, 0.4)',
      borderColor: '#FFB74D',
    }
  } else if (nodeData._isHighCost) {
    boxOverrides = {
      boxShadow: '0 0 16px 4px rgba(255, 204, 0, 0.4)',
      borderColor: '#FFCA28',
    }
  } else if (nodeData._isHighLatency) {
    boxOverrides = {
      boxShadow: '0 0 16px 4px rgba(204, 0, 0, 0.4)',
      borderColor: '#EF5350',
    }
  }

  return {
    ...baseStyle,
    ...errorOverrides,
    ...boxOverrides,
    width: nodeData._scaledWidth ?? NODE_WIDTH,
    height: nodeData._scaledHeight ?? NODE_HEIGHT,
    padding: '6px 10px',
    opacity: nodeData._isDimmed ? 0.2 : 1.0,
    transition: 'opacity 0.3s ease, background 0.3s ease, border 0.3s ease, width 0.3s ease, height 0.3s ease, box-shadow 0.3s ease, padding 0.3s ease',
  }
}

// Unused legacy styles removed


function getErrorStyles(errorCount: number): React.CSSProperties {
  if (errorCount > 0) {
    return {
      borderColor: '#FF5252',
      boxShadow: '0 0 12px rgba(255, 82, 82, 0.4)',
    }
  }
  return {}
}

function formatLatency(ms: number | undefined): string {
  if (ms === undefined || ms === null) return '0ms'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
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

function formatTokens(n: number | undefined): string {
  if (n === undefined || n === null) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function MetricBadges({ nodeData: baseNodeData }: { nodeData: TopologyNode['data'] }) {
  const nodeData = baseNodeData as NodeDataExtended

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginTop: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#94A3B8', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
        {nodeData.avgDurationMs !== undefined && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 2, color: nodeData._isHighLatency ? '#EF5350' : '#94A3B8', textShadow: nodeData._isHighLatency ? '0 0 8px rgba(239, 83, 80, 0.5)' : 'none' }}>
            <Activity size={12} />
            {formatLatency(nodeData.avgDurationMs)}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
        {nodeData.totalTokens !== undefined && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 2, color: nodeData._isHighCost ? '#FFCA28' : '#94A3B8', textShadow: nodeData._isHighCost ? '0 0 8px rgba(255, 202, 40, 0.5)' : 'none' }}>
            <FileDigit size={12} />
            {formatTokens(nodeData.totalTokens)}
          </div>
        )}
        {nodeData.errorCount > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 2, color: '#FF5252' }}>
            <AlertCircle size={12} />
            {nodeData.errorCount}
          </div>
        )}
      </div>
    </div>
  )
}

type NodeDataExtended = TopologyNode['data'] & {
  _layoutMode?: string
  _heatColor?: string
  _scaledWidth?: number
  _scaledHeight?: number
  _isHighCost?: boolean
  _isHighLatency?: boolean
  _sparklinePoints?: TimeSeriesPoint[]
  _isDimmed?: boolean
  _expanded?: boolean
  _hasChildren?: boolean
  _childrenCount?: number
  _onToggleExpand?: () => void
}

function NodeSparkline({ nodeData }: { nodeData: NodeDataExtended }) {
  if (!nodeData._sparklinePoints || nodeData._sparklinePoints.length < 2) return null
  const series = extractSparkSeries(nodeData._sparklinePoints, 'latency')
  const width = nodeData._scaledWidth ? nodeData._scaledWidth - 24 : NODE_WIDTH - 24
  return <Sparkline data={series} color={sparkColor('latency')} width={width} />
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
        top: -10,
        right: -10,
        background: '#1E293B',
        border: '1px solid #06B6D4',
        borderRadius: 12,
        padding: '2px 8px',
        fontSize: 10,
        fontFamily: "'JetBrains Mono', monospace",
        color: '#F0F4F8',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        zIndex: 10,
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
      }}
    >
      {nodeData._expanded ? (
        <Minus size={12} color="#EF4444" strokeWidth={3} />
      ) : (
        <>
          <Plus size={12} color="#10B981" strokeWidth={3} />
          <span>({nodeData._childrenCount})</span>
        </>
      )}
    </div>
  )
}


function NodeContent({ nodeData, icon: IconComponent, iconColor, labelOverride }: { nodeData: NodeDataExtended, icon: React.ElementType, iconColor: string, labelOverride?: string }) {
  const label = labelOverride || nodeData.label || 'User'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
        <IconComponent size={14} color={iconColor} style={{ flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flexGrow: 1 }}>
          {label}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', width: '100%', flexGrow: 1 }}>
        <div style={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <NodeSparkline nodeData={nodeData} />
        </div>
        <MetricBadges nodeData={nodeData} />
      </div>
      <ExpandButton nodeData={nodeData} />
    </div>
  )
}

function UserNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const isVertical = nodeData._layoutMode === 'vertical'
  return (
    <div style={BaseNodeStyle(nodeData, nodeStyles.user)}>
      <NodeContent nodeData={nodeData} icon={User} iconColor="#06B6D4" labelOverride="User" />
      <Handle type="source" position={isVertical ? Position.Bottom : Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}

function AgentNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const isSubAgent = nodeData.nodeType?.toLowerCase() === 'sub_agent'
  const isVertical = nodeData._layoutMode === 'vertical'
  return (
    <div style={BaseNodeStyle(nodeData, isSubAgent ? nodeStyles.sub_agent : nodeStyles.agent)}>
      <Handle type="target" position={isVertical ? Position.Top : Position.Left} style={{ opacity: 0 }} />
      <NodeContent nodeData={nodeData} icon={Bot} iconColor={isSubAgent ? "#00ACC1" : "#26A69A"} />
      <Handle type="source" position={isVertical ? Position.Bottom : Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}

function ToolNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const isVertical = nodeData._layoutMode === 'vertical'
  return (
    <div style={BaseNodeStyle(nodeData, nodeStyles.tool)}>
      <Handle type="target" position={isVertical ? Position.Top : Position.Left} style={{ opacity: 0 }} />
      <NodeContent nodeData={nodeData} icon={Wrench} iconColor="#FFA726" />
      <Handle type="source" position={isVertical ? Position.Bottom : Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}

function LLMNode({ data }: NodeProps) {
  const nodeData = data as NodeDataExtended
  const isVertical = nodeData._layoutMode === 'vertical'
  return (
    <div style={BaseNodeStyle(nodeData, nodeStyles.llm)}>
      <Handle type="target" position={isVertical ? Position.Top : Position.Left} style={{ opacity: 0 }} />
      <NodeContent nodeData={nodeData} icon={Sparkles} iconColor="#ba68c8" />
      <Handle type="source" position={isVertical ? Position.Bottom : Position.Right} style={{ opacity: 0 }} />
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

interface TopologyGraphProps {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  sparklineData?: TimeSeriesData | null
  onNodeClick?: (nodeId: string) => void
  onEdgeClick?: (sourceId: string, targetId: string) => void
  selectedNodeId?: string | null
}

export default function TopologyGraph({
  nodes,
  edges,
  sparklineData,
  onNodeClick,
  onEdgeClick,
  selectedNodeId
}: TopologyGraphProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('horizontal')
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
        0%, 100% { box-shadow: 0 0 0 0 rgba(255, 82, 82, 0.4); }
        50% { box-shadow: 0 0 12px 4px rgba(255, 82, 82, 0.6); }
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
      let scaledWidth: number | undefined
      let scaledHeight: number | undefined
      let isHighCost = false
      let isHighLatency = false

      const tokens = n.data.totalTokens ?? 0
      const costRatio = maxTokens > 0 ? tokens / maxTokens : 0
      if (costRatio > 0.7 && tokens > 1000) {
        isHighCost = true
      }

      const lat = n.data.avgDurationMs ?? 0
      const latRatio = maxLatency > 0 ? lat / maxLatency : 0
      if (latRatio > 0.7 && lat > 500) {
        isHighLatency = true
      }

      // Slightly scale up nodes that are hotspots
      const maxRatio = Math.max(costRatio, latRatio)
      if (maxRatio > 0.5) {
        const dims = getScaledDimensions(maxRatio * 0.5) // Less aggressive scaling
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
          _layoutMode: layoutMode,
          _scaledWidth: scaledWidth,
          _scaledHeight: scaledHeight,
          _isHighCost: isHighCost,
          _isHighLatency: isHighLatency,
          _sparklinePoints: sparkPoints,
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
  }, [nodes, sparklineData, expandedIds, topology, selectedNodeId, highlightedPath, layoutMode])

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
          stroke: hasErrors ? '#FF5252' : (isBackEdge ? '#06B6D4' : '#334155'),
          strokeWidth,
          opacity: isDimmed ? 0.2 : 1.0,
          transition: 'opacity 0.3s ease',
        },
        label: `${e.data.callCount} calls`,
        labelStyle: { fill: '#78909C', fontSize: 11, opacity: isDimmed ? 0.2 : 1.0, fontFamily: "'JetBrains Mono', monospace" },
        labelBgStyle: { fill: '#0F172A', fillOpacity: isDimmed ? 0.2 : 0.8 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 4,
      }
    })
  }, [expandedIds, topology, selectedNodeId, highlightedPath])

  const [rfNodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  const doLayout = useCallback((mode: LayoutMode = layoutMode) => {
    const rawNodes = toReactFlowNodes()
    const rawEdges = toReactFlowEdges()
    const { nodes: layouted, edges: layoutedEdges } = getLayoutedElements(
      rawNodes,
      rawEdges,
      mode
    )
    setNodes(layouted)
    setEdges(layoutedEdges)
  }, [toReactFlowNodes, toReactFlowEdges, setNodes, setEdges, layoutMode])

  useEffect(() => {
    doLayout(layoutMode)
  }, [doLayout, layoutMode])

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
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
    <div style={{ width: '100%', height: '100%', background: '#0F172A', position: 'relative' }}>
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
        colorMode="dark"
      >
        <Background color="#334155" gap={20} />
        <Panel position="top-left" style={{ margin: 16, background: '#1E293B', border: '1px solid #334155', borderRadius: '8px', padding: '8px', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace", display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Network size={14} /> Layout:
          </span>
          <select
            style={{
              background: '#0F172A', color: '#F0F4F8', border: '1px solid #334155',
              borderRadius: '4px', padding: '4px 8px', fontSize: '12px', outline: 'none', cursor: 'pointer'
            }}
            value={layoutMode}
            onChange={(e) => {
              const val = e.target.value as LayoutMode
              setLayoutMode(val)
            }}
          >
            <option value="horizontal">Horizontal</option>
            <option value="vertical">Vertical</option>
            <option value="cluster">Grouped by Type</option>
          </select>
        </Panel>

        <Controls
          position="top-right"
          style={{ background: '#1E293B', border: '1px solid #334155', borderRadius: '6px' }}
        >
          <ControlButton
            title="Expand All"
            onClick={() => {
              const allIds = new Set(nodes.map(n => n.id))
              setExpandedIds(allIds)
            }}
          >
            <UnfoldHorizontal size={16} />
          </ControlButton>
          <ControlButton
            title="Collapse Sub-Agents"
            onClick={() => {
              const rootIds = new Set(topology.rootIds)
              setExpandedIds(rootIds)
            }}
          >
            <FoldHorizontal size={16} />
          </ControlButton>
          <ControlButton
            title="Re-layout Graph"
            onClick={() => doLayout()}
          >
            <LayoutTemplate size={16} />
          </ControlButton>
        </Controls>
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
          maskColor="rgba(15, 23, 42, 0.8)"
          style={{ background: '#1E293B', border: '1px solid #334155', borderRadius: '6px' }}
        />

      </ReactFlow>
    </div>
  )
}
