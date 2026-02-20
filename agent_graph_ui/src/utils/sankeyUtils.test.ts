import { describe, it, expect } from 'vitest'
import { removeCyclicLinks } from './sankeyUtils'
import type { SankeyResponse } from '../types'

describe('removeCyclicLinks', () => {
  it('should not remove any links from an acyclic graph (DAG)', () => {
    const data: SankeyResponse = {
      nodes: [
        { id: 'Agent::A', nodeColor: '#000' },
        { id: 'Tool::B', nodeColor: '#000' },
        { id: 'LLM::C', nodeColor: '#000' },
      ],
      links: [
        { source: 'Agent::A', target: 'Tool::B', value: 1 },
        { source: 'Tool::B', target: 'LLM::C', value: 2 },
        { source: 'Agent::A', target: 'LLM::C', value: 3 }, // Cross-edge, perfectly fine DAG
      ],
    }
    const result = removeCyclicLinks(data)
    expect(result.nodes).toHaveLength(3)
    expect(result.links).toHaveLength(3)
  })

  it('should drop a simple back-edge (direct cycle) and retain valid nodes/links', () => {
    const data: SankeyResponse = {
      nodes: [
        { id: 'A', nodeColor: '#000' },
        { id: 'B', nodeColor: '#000' },
      ],
      links: [
        { source: 'A', target: 'B', value: 1 },
        { source: 'B', target: 'A', value: 2 }, // Direct cycle (back-edge)
      ],
    }
    const result = removeCyclicLinks(data)
    expect(result.nodes).toHaveLength(2)
    // One of them is a back-edge and should be dropped. The DFS starts with A probably (in-degree).
    expect(result.links).toHaveLength(1)
    expect(result.links[0]?.source).toBe('A') // Given sort heuristic, starts at A
  })

  it('should remove a multi-hop cycle (A->B->C->B)', () => {
    const data: SankeyResponse = {
      nodes: [
        { id: 'A', nodeColor: '#000' },
        { id: 'B', nodeColor: '#000' },
        { id: 'C', nodeColor: '#000' },
      ],
      links: [
        { source: 'A', target: 'B', value: 1 },
        { source: 'B', target: 'C', value: 2 },
        { source: 'C', target: 'B', value: 3 }, // Long cycle
      ],
    }
    const result = removeCyclicLinks(data)
    expect(result.nodes).toHaveLength(3)
    expect(result.links).toHaveLength(2)
    expect(result.links.find((l) => l.source === 'C' && l.target === 'B')).toBeUndefined()
  })

  it('handles isolated nodes or disconnected components without throwing', () => {
    const data: SankeyResponse = {
      nodes: [
        { id: 'A', nodeColor: '#000' }, // Component 1
        { id: 'B', nodeColor: '#000' }, // Component 1
        { id: 'C', nodeColor: '#000' }, // Isolated
        { id: 'D', nodeColor: '#000' }, // Component 2
        { id: 'E', nodeColor: '#000' }, // Component 2
      ],
      links: [
        { source: 'A', target: 'B', value: 1 },
        { source: 'D', target: 'E', value: 2 },
        { source: 'E', target: 'D', value: 3 }, // Cyclical component
      ],
    }
    const result = removeCyclicLinks(data)
    expect(result.nodes).toHaveLength(5)
    // E->D is cyclical
    expect(result.links).toHaveLength(2)
    expect(result.links.find((l) => l.source === 'A' && l.target === 'B')).toBeDefined()
    expect(result.links.find((l) => l.source === 'D' && l.target === 'E')).toBeDefined()
    expect(result.links.find((l) => l.source === 'E' && l.target === 'D')).toBeUndefined()
  })
})
