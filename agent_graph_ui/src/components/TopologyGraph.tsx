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

function AgentNode({ data }: NodeProps) {
  const nodeData = data as TopologyNode['data']
  return (
    <div style={nodeStyles.agent}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Executions: {nodeData.executionCount}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function ToolNode({ data }: NodeProps) {
  const nodeData = data as TopologyNode['data']
  return (
    <div style={nodeStyles.tool}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Calls: {nodeData.executionCount}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function LLMNode({ data }: NodeProps) {
  const nodeData = data as TopologyNode['data']
  return (
    <div style={nodeStyles.llm}>
      <Handle type="target" position={Position.Left} />
      <div>{nodeData.label}</div>
      <div style={subtextStyle}>Tokens: {nodeData.totalTokens}</div>
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
}

export default function TopologyGraph({ nodes, edges }: TopologyGraphProps) {
  const toReactFlowNodes = useCallback((): Node[] => {
    return nodes.map((n) => ({
      id: n.id,
      type: mapNodeType(n.data.nodeType),
      data: n.data,
      position: n.position,
    }))
  }, [nodes])

  const toReactFlowEdges = useCallback((): Edge[] => {
    return edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: true,
      style: { stroke: '#30363d', strokeWidth: 2 },
      label: `${e.data.callCount} calls`,
      labelStyle: { fill: '#8b949e', fontSize: 11 },
      labelBgStyle: { fill: '#0d1117', fillOpacity: 0.8 },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 4,
    }))
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

  return (
    <div style={{ flex: 1, minHeight: '500px', background: '#0d1117', borderRadius: '8px' }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
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
