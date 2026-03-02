export interface TimelineItem {
  id: string
  timestamp: string
}

export interface PositionedItem<T extends TimelineItem> {
  item: T
  y: number
}

/**
 * Calculate evenly-spaced Y positions for timeline events ordered by timestamp.
 */
export function calculateTimelinePositions<T extends TimelineItem>(
  events: T[],
  height: number,
  padding = 40,
): PositionedItem<T>[] {
  if (events.length === 0) return []

  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  )

  const usable = height - padding * 2
  const step = sorted.length > 1 ? usable / (sorted.length - 1) : 0

  return sorted.map((item, i) => ({
    item,
    y: padding + i * step,
  }))
}
