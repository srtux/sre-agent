import { describe, it, expect } from 'vitest'
import { GraphTopologyHelper } from './topology'
import type { TopologyNode, TopologyEdge } from '../types'

describe('GraphTopologyHelper', () => {
  const mockNodes: TopologyNode[] = [
    { id: '1', type: 'user', data: { label: 'User', nodeType: 'user', executionCount: 1, totalTokens: 0, errorCount: 0, avgDurationMs: 0 }, position: { x: 0, y: 0 } },
    { id: '2', type: 'agent', data: { label: 'Agent1', nodeType: 'agent', executionCount: 1, totalTokens: 10, errorCount: 0, avgDurationMs: 100 }, position: { x: 0, y: 0 } },
    { id: '3', type: 'tool', data: { label: 'Tool1', nodeType: 'tool', executionCount: 1, totalTokens: 5, errorCount: 0, avgDurationMs: 50 }, position: { x: 0, y: 0 } },
    { id: '4', type: 'agent', data: { label: 'Agent2', nodeType: 'agent', executionCount: 1, totalTokens: 20, errorCount: 0, avgDurationMs: 200 }, position: { x: 0, y: 0 } },
  ]

  it('should identify user nodes as roots', () => {
    const edges: TopologyEdge[] = [
      { id: 'e1', source: '1', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 100 } }
    ]
    const topology = GraphTopologyHelper.analyze(mockNodes, edges)
    expect(topology.rootIds).toContain('1')
  })

  it('should detect direct cycle back-edges', () => {
    const edges: TopologyEdge[] = [
      { id: 'e1', source: '1', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 100 } },
      { id: 'e2', source: '2', target: '3', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } },
      { id: 'e3', source: '3', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } } // cycle
    ]
    const topology = GraphTopologyHelper.analyze(mockNodes, edges)
    expect(topology.backEdgePairs.has('3->2')).toBe(true)
    expect(topology.dagEdges.length).toBe(2)
  })

  it('should detect multi-hop cycle back-edges', () => {
    const edges: TopologyEdge[] = [
      { id: 'e1', source: '1', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 100 } },
      { id: 'e2', source: '2', target: '3', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } },
      { id: 'e3', source: '3', target: '4', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } },
      { id: 'e4', source: '4', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } } // cycle
    ]
    const topology = GraphTopologyHelper.analyze(mockNodes, edges)
    expect(topology.backEdgePairs.has('4->2')).toBe(true)
    expect(topology.dagEdges.length).toBe(3)
  })

  it('should compute path upstream and downstream using computePath', () => {
    const edges: TopologyEdge[] = [
      { id: 'e1', source: '1', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 100 } },
      { id: 'e2', source: '2', target: '3', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } },
      { id: 'e3', source: '3', target: '4', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } }
    ]
    const topology = GraphTopologyHelper.analyze(mockNodes, edges)
    // Select node 3: should go back to 2 and 1, and forward to 4
    const path = topology.computePath('3')
    expect(path.has('1')).toBe(true)
    expect(path.has('2')).toBe(true)
    expect(path.has('3')).toBe(true)
    expect(path.has('4')).toBe(true)
  })

  it('should track descendants count correctly', () => {
    const edges: TopologyEdge[] = [
      { id: 'e1', source: '1', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 100 } },
      { id: 'e2', source: '2', target: '3', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } },
      { id: 'e3', source: '2', target: '4', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } }
    ]
    const topology = GraphTopologyHelper.analyze(mockNodes, edges)
    expect(topology.getChildrenCount('1')).toBe(3) // 2, 3, 4
    expect(topology.getChildrenCount('2')).toBe(2) // 3, 4
    expect(topology.getChildrenCount('3')).toBe(0)
  })

  it('getVisibleGraph should return only expanded nodes and edges', () => {
    const edges: TopologyEdge[] = [
      { id: 'e1', source: '1', target: '2', data: { callCount: 1, errorCount: 0, avgDurationMs: 100 } },
      { id: 'e2', source: '2', target: '3', data: { callCount: 1, errorCount: 0, avgDurationMs: 50 } }
    ]
    const topology = GraphTopologyHelper.analyze(mockNodes, edges)

    // Only root expanded
    let expandedIds = new Set(['1'])
    let visible = topology.getVisibleGraph(expandedIds)
    expect(visible.nodes.map(n => n.id)).toEqual(expect.arrayContaining(['1', '2']))
    expect(visible.nodes.find(n => n.id === '3')).toBeUndefined()
    expect(visible.dagEdges.length).toBe(1)

    // Expand node 2 as well
    expandedIds = new Set(['1', '2'])
    visible = topology.getVisibleGraph(expandedIds)
    expect(visible.nodes.map(n => n.id)).toEqual(expect.arrayContaining(['1', '2', '3']))
    expect(visible.dagEdges.length).toBe(2)
  })
})
