export interface TopologyNode {
  id: string;
  type: string;
  data: {
    label: string;
    nodeType: string;
    executionCount: number;
    totalTokens: number;
    errorCount: number;
    avgDurationMs?: number;
  };
  position: { x: number; y: number };
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  data: {
    callCount: number;
    avgDurationMs: number;
    errorCount: number;
    totalTokens?: number;
  };
}

export interface TopologyResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface SankeyNode {
  id: string;
  nodeColor: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyResponse {
  nodes: SankeyNode[];
  links: SankeyLink[];
}
