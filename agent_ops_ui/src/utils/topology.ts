import type { TopologyNode, TopologyEdge } from '../types'

/**
 * Result of getVisibleGraph spanning both Directed Acyclic Graph structures
 * and cyclically-recurrent back-edges.
 */
export interface VisibleGraph {
  nodes: TopologyNode[]
  dagEdges: TopologyEdge[]
  backEdges: TopologyEdge[]
}

/**
 * Utility for analyzing graph topology using Iterative DFS and three-set coloring.
 * Extracts a strict DAG for predictable layout alongside a separate set of back-edges (cycles).
 * Provides methods for progressive disclosure (expanding/collapsing subtrees)
 * and upstream/downstream drill-down via BFS (computePath).
 */
export class GraphTopologyHelper {
  backEdgePairs: Set<string>
  dagEdges: TopologyEdge[]
  nodeDepths: Map<string, number>
  nodeMap: Map<string, TopologyNode>
  adjAll: Map<string, TopologyEdge[]>
  adjDag: Map<string, TopologyEdge[]>
  rootIds: string[]
  allEdges: TopologyEdge[]

  /**
   * Internal constructor. Use static `analyze` instead.
   */
  constructor(
    backEdgePairs: Set<string>,
    dagEdges: TopologyEdge[],
    nodeDepths: Map<string, number>,
    nodeMap: Map<string, TopologyNode>,
    adjAll: Map<string, TopologyEdge[]>,
    adjDag: Map<string, TopologyEdge[]>,
    rootIds: string[],
    allEdges: TopologyEdge[]
  ) {
    this.backEdgePairs = backEdgePairs
    this.dagEdges = dagEdges
    this.nodeDepths = nodeDepths
    this.nodeMap = nodeMap
    this.adjAll = adjAll
    this.adjDag = adjDag
    this.rootIds = rootIds
    this.allEdges = allEdges
  }

  /**
   * Analyzes an unsorted list of nodes and edges, identifying back-edges
   * via DFS 3-color detection, mapping out degrees, and separating the
   * topology into DAG vs strictly recurrent elements.
   *
   * @param nodes The full array of TopologyNode items from the backend
   * @param edges The full array of TopologyEdge items from the backend
   * @returns Configured GraphTopologyHelper instance
   */
  static analyze(nodes: TopologyNode[], edges: TopologyEdge[]): GraphTopologyHelper {
    const nodeMap = new Map<string, TopologyNode>()
    for (const n of nodes) {
      nodeMap.set(n.id, n)
    }

    const adjAll = new Map<string, TopologyEdge[]>()
    const inDegree = new Map<string, number>()
    for (const e of edges) {
      if (!adjAll.has(e.source)) adjAll.set(e.source, [])
      adjAll.get(e.source)!.push(e)
      inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1)
    }

    // Determine root nodes
    const rootIds: string[] = []
    const userNodes = nodes.filter((n) => n.data.label.toLowerCase() === 'user' || n.type === 'user').map(n => n.id)

    if (userNodes.length > 0) {
      rootIds.push(...userNodes)
    } else {
      // Find zero in-degree nodes
      for (const n of nodes) {
        if (!inDegree.has(n.id) || inDegree.get(n.id) === 0) {
          rootIds.push(n.id)
        }
      }
    }

    // Fallback if pure cycle
    if (rootIds.length === 0 && nodes.length > 0) {
      const outDegree = new Map<string, number>()
      for (const e of edges) {
        outDegree.set(e.source, (outDegree.get(e.source) || 0) + 1)
      }
      let bestId = nodes[0].id
      let bestOut = outDegree.get(bestId) || 0
      for (const n of nodes) {
        const out = outDegree.get(n.id) || 0
        if (out > bestOut) {
          bestOut = out
          bestId = n.id
        }
      }
      rootIds.push(bestId)
    }

    // DFS with 3-color cycle detection
    const WHITE = 0, GRAY = 1, BLACK = 2
    const color = new Map<string, number>()
    for (const n of nodes) {
      color.set(n.id, WHITE)
    }

    const backEdgePairs = new Set<string>()
    const nodeDepths = new Map<string, number>()

    for (const rootId of rootIds) {
      if (color.get(rootId) !== WHITE) continue

      // stack: [nodeId, edgeIndex, depth]
      const stack: [string, number, number][] = [[rootId, 0, 0]]
      color.set(rootId, GRAY)
      nodeDepths.set(rootId, 0)

      while (stack.length > 0) {
        const frame = stack[stack.length - 1]
        const [nodeId, edgeIdx, depth] = frame
        const children = adjAll.get(nodeId) || []

        if (edgeIdx < children.length) {
          stack[stack.length - 1][1]++ // Increment edgeIdx
          const edge = children[edgeIdx]
          const childId = edge.target
          const childColor = color.get(childId) ?? WHITE

          if (childColor === GRAY) {
            // Back-edge
            backEdgePairs.add(`${edge.source}->${edge.target}`)
          } else if (childColor === WHITE) {
            color.set(childId, GRAY)
            nodeDepths.set(childId, depth + 1)
            stack.push([childId, 0, depth + 1])
          }
        } else {
          color.set(nodeId, BLACK)
          stack.pop()
        }
      }
    }

    // Handle disconnected components
    for (const n of nodes) {
      if (color.get(n.id) === WHITE) {
        nodeDepths.set(n.id, 0)
        const stack: [string, number, number][] = [[n.id, 0, 0]]
        color.set(n.id, GRAY)

        while (stack.length > 0) {
          const frame = stack[stack.length - 1]
          const [nodeId, edgeIdx, depth] = frame
          const children = adjAll.get(nodeId) || []

          if (edgeIdx < children.length) {
            stack[stack.length - 1][1]++
            const edge = children[edgeIdx]
            const childId = edge.target
            const childColor = color.get(childId) ?? WHITE

            if (childColor === GRAY) {
              backEdgePairs.add(`${edge.source}->${edge.target}`)
            } else if (childColor === WHITE) {
              color.set(childId, GRAY)
              nodeDepths.set(childId, depth + 1)
              stack.push([childId, 0, depth + 1])
            }
          } else {
            color.set(nodeId, BLACK)
            stack.pop()
          }
        }
      }
    }

    const dagEdges = edges.filter(e => !backEdgePairs.has(`${e.source}->${e.target}`))
    const adjDag = new Map<string, TopologyEdge[]>()
    for (const e of dagEdges) {
      if (!adjDag.has(e.source)) adjDag.set(e.source, [])
      adjDag.get(e.source)!.push(e)
    }

    return new GraphTopologyHelper(
      backEdgePairs,
      dagEdges,
      nodeDepths,
      nodeMap,
      adjAll,
      adjDag,
      rootIds,
      edges
    )
  }

  /**
   * Produces a filtered scope of `topology.nodes` and `topology.dagEdges` based on
   * the provided set of explicitly expanded node string identifiers.
   * Back-edges are merged back in only if both endpoints independently pass
   * the expansion filter checking.
   *
   * @param expandedNodeIds The Set of IDs permitted to reveal their downstream edges
   * @returns VisibleGraph the unified subset graph permitted by the current progressive disclosure
   */
  getVisibleGraph(expandedNodeIds: Set<string>): VisibleGraph {
    const visibleIds = new Set<string>()
    const visibleDagEdges: TopologyEdge[] = []

    const queue: string[] = [...this.rootIds]
    const visited = new Set<string>(this.rootIds)
    for (const id of this.rootIds) {
      visibleIds.add(id)
    }

    while (queue.length > 0) {
      const nodeId = queue.shift()!

      if (!expandedNodeIds.has(nodeId)) continue

      const edges = this.adjDag.get(nodeId) || []
      for (const edge of edges) {
        visibleDagEdges.push(edge)
        if (!visited.has(edge.target)) {
          visited.add(edge.target)
          visibleIds.add(edge.target)
          queue.push(edge.target)
        }
      }
    }

    const visibleNodes: TopologyNode[] = []
    for (const id of visibleIds) {
      const node = this.nodeMap.get(id)
      if (node) visibleNodes.push(node)
    }

    const visibleBackEdges: TopologyEdge[] = []
    for (const backEdgeKey of this.backEdgePairs) {
      const [source, target] = backEdgeKey.split('->')
      if (visibleIds.has(source) && visibleIds.has(target)) {
        const edges = this.adjAll.get(source) || []
        for (const e of edges) {
          if (e.target === target) {
            visibleBackEdges.push(e)
            break
          }
        }
      }
    }

    return {
      nodes: visibleNodes,
      dagEdges: visibleDagEdges,
      backEdges: visibleBackEdges
    }
  }

  /**
   * Executes Bidirectional Breadth-First-Search from `targetId` to identify all nodes
   * causally connected up or down the stream from the target node parameter.
   *
   * @param targetId The root node to analyze bidirectional reachability from
   * @returns A distinct Set of IDs matching the traced traversal path
   */
  computePath(targetId: string): Set<string> {
    const pathIds = new Set<string>()
    pathIds.add(targetId)

    // Upstream (Reverse BFS)
    const revAdj = new Map<string, string[]>()
    for (const e of this.allEdges) {
      if (!revAdj.has(e.target)) revAdj.set(e.target, [])
      revAdj.get(e.target)!.push(e.source)
    }

    const pQueue = [targetId]
    while (pQueue.length > 0) {
      const curr = pQueue.shift()!
      const parents = revAdj.get(curr) || []
      for (const p of parents) {
        if (!pathIds.has(p)) {
          pathIds.add(p)
          pQueue.push(p)
        }
      }
    }

    // Downstream (Forward BFS)
    const dQueue = [targetId]
    while (dQueue.length > 0) {
      const curr = dQueue.shift()!
      const children = this.adjAll.get(curr) || []
      for (const edge of children) {
        const child = edge.target
        if (!pathIds.has(child)) {
          pathIds.add(child)
          dQueue.push(child)
        }
      }
    }

    return pathIds
  }

  /**
   * Identifies all recursive downstream descendants mapping off a specific parent.
   */
  getChildrenCount(nodeId: string): number {
    // Collect all descendants in the DAG mapping
    const descendants = new Set<string>()
    const queue = [nodeId]
    while (queue.length > 0) {
      const curr = queue.shift()!
      const edges = this.adjDag.get(curr) || []
      for (const e of edges) {
        if (!descendants.has(e.target)) {
          descendants.add(e.target)
          queue.push(e.target)
        }
      }
    }
    return descendants.size
  }

  /**
   * Helper check returning true if this node spans any downstream routes whatsoever.
   */
  hasChildren(nodeId: string): boolean {
    return (this.adjAll.get(nodeId) || []).length > 0
  }
}
