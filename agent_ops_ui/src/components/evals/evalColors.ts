/** Colour palette per metric – deterministic mapping. */
export const METRIC_COLORS: Record<string, string> = {
  coherence: '#06B6D4',
  groundedness: '#8B5CF6',
  fluency: '#10B981',
  safety: '#F59E0B',
  relevance: '#EC4899',
  faithfulness: '#3B82F6',
}

export function colorForMetric(name: string): string {
  return METRIC_COLORS[name.toLowerCase()] ?? '#94A3B8'
}
