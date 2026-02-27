import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useState, useEffect } from 'react'
import { Edge, Node } from '@xyflow/react'
import { useAgentContext } from '../contexts/AgentContext'
import { ContextNode, ContextEdge } from '../types/graphTypes'
import { getLayoutedElements } from '../utils/graphLayout'

export const useAgentGraph = (sessionId: string | null) => {
  const { projectId } = useAgentContext()

  const query = useQuery({
    queryKey: ['context-graph', projectId, sessionId],
    queryFn: async () => {
      const { data } = await axios.get<{ nodes: ContextNode[], edges: ContextEdge[] }>(
        `/api/v1/graph/context/${sessionId}`,
        { params: { project_id: projectId } }
      )
      return data
    },
    enabled: !!projectId && !!sessionId,
    staleTime: 30_000,
  })

  const [data, setData] = useState<{ nodes: Node[], edges: Edge[] }>({ nodes: [], edges: [] })

  useEffect(() => {
    if (!query.data || query.data.nodes.length === 0) {
      setData({ nodes: [], edges: [] })
      return
    }

    const { nodes: backendNodes, edges: backendEdges } = query.data

    const nodes: Node[] = backendNodes.map(n => ({
      id: String(n.id),
      data: n,
      position: { x: 0, y: 0 },
      type: n.type
    }))

    const edges: Edge[] = backendEdges.map((e, index) => ({
      id: `e${e.source}-${e.target}-${index}`,
      source: String(e.source),
      target: String(e.target),
      label: e.label,
      animated: true,
      type: 'smoothstep',
      style: { stroke: '#94A3B8', strokeWidth: 2 },
      labelStyle: { fill: '#94A3B8', fontWeight: 600, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" },
      labelBgStyle: { fill: '#1E293B' },
      labelBgPadding: [4, 4],
      labelBgBorderRadius: 4,
    }))

    const layouted = getLayoutedElements(nodes, edges, 'LR')
    setData({ nodes: layouted.nodes, edges: layouted.edges })
  }, [query.data])

  return data
}
