import type { SankeyResponse } from '../types'

/**
 * Removes cyclic links from a Sankey graph response to prevent rendering crashes in Nivo.
 * This performs a Depth First Search (DFS) on the graph. It tracks the recursion stack
 * to identify back-edges (cycles) and drops them from the resulting safe dataset.
 *
 * @param data The original graph topology data with potential cycles.
 * @returns A new object with cyclic edges removed for safe rendering.
 */
export function removeCyclicLinks(data: SankeyResponse): SankeyResponse {
  // 1. Validate nodes exist for all links
  const validNodeIds = new Set(data.nodes.map((n) => n.id))
  // Filter out any links whose source or target refers to a non-existent node
  const validLinks = data.links.filter(
    (l) => validNodeIds.has(l.source) && validNodeIds.has(l.target),
  )

  const safeLinks: SankeyResponse['links'] = []
  const visited = new Set<string>()
  const recStack = new Set<string>()

  const adj = new Map<string, { target: string; link: SankeyResponse['links'][0] }[]>()
  data.nodes.forEach((n) => adj.set(n.id, []))
  validLinks.forEach((l) => {
    if (!adj.has(l.source)) adj.set(l.source, [])
    if (!adj.has(l.target)) adj.set(l.target, [])
    adj.get(l.source)!.push({ target: l.target, link: l })
  })

  // Calculate in-degree for a heuristic start order (roots first)
  const inDegree = new Map<string, number>()
  data.nodes.forEach((n) => inDegree.set(n.id, 0))
  validLinks.forEach((l) => {
    inDegree.set(l.target, (inDegree.get(l.target) ?? 0) + 1)
  })

  const sortedNodes = [...data.nodes].sort(
    (a, b) => (inDegree.get(a.id) ?? 0) - (inDegree.get(b.id) ?? 0),
  )

  function dfs(node: string) {
    visited.add(node)
    recStack.add(node)

    const neighbors = adj.get(node) || []
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor.target)) {
        safeLinks.push(neighbor.link)
        dfs(neighbor.target)
      } else if (!recStack.has(neighbor.target)) {
        // visited but not in recStack means it's a cross/forward edge, safe
        safeLinks.push(neighbor.link)
      } else {
        // It's in the recStack, which means this is a cycle (back-edge). Drop it.
        console.warn(`Dropped cyclic sankey link: ${node} -> ${neighbor.target}`)
      }
    }
    recStack.delete(node)
  }

  for (const node of sortedNodes) {
    if (!visited.has(node.id)) {
      dfs(node.id)
    }
  }

  // 2. Aggregate parallel edges. d3-sankey often crashes if multiple identical edges exist.
  const aggregatedLinks = new Map<string, SankeyResponse['links'][0]>()
  for (const link of safeLinks) {
    const simpleKey = `${link.source}->${link.target}`
    if (aggregatedLinks.has(simpleKey)) {
      aggregatedLinks.get(simpleKey)!.value += link.value
    } else {
      aggregatedLinks.set(simpleKey, { ...link })
    }
  }

  return { ...data, nodes: data.nodes, links: Array.from(aggregatedLinks.values()) }
}
