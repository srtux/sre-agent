/**
 * A2UI (Agent-to-UI) protocol types.
 * Ported from autosre/lib/catalog.dart
 */

/** A surface represents a rendered widget area in the chat. */
export interface Surface {
  id: string
  componentName: string
  data: Record<string, unknown>
  status: 'rendering' | 'complete'
}

/** Begin rendering a new A2UI surface. */
export interface BeginRendering {
  action: 'beginRendering'
  surfaceId: string
  componentName: string
  data?: Record<string, unknown>
}

/** Update an existing A2UI surface with new data. */
export interface SurfaceUpdate {
  action: 'surfaceUpdate'
  surfaceId: string
  data: Record<string, unknown>
}

/** End rendering of an A2UI surface. */
export interface EndRendering {
  action: 'endRendering'
  surfaceId: string
}

export type A2UIAction = BeginRendering | SurfaceUpdate | EndRendering

/**
 * Unwrap component data from various possible wrapper formats.
 * Handles: direct key, component wrapper, root type match, and fallback.
 */
export function unwrapComponentData(
  rawData: unknown,
  componentName: string,
): Record<string, unknown> {
  if (!rawData || typeof rawData !== 'object') return {}

  const data = rawData as Record<string, unknown>

  // 1. Direct key match: {"x-sre-foo": {...}}
  if (data[componentName] && typeof data[componentName] === 'object') {
    return data[componentName] as Record<string, unknown>
  }

  // 2. Component wrapper: {"component": {"x-sre-foo": {...}}}
  if (data.component && typeof data.component === 'object') {
    const component = data.component as Record<string, unknown>
    if (component[componentName]) {
      return component[componentName] as Record<string, unknown>
    }
    if (component.type === componentName) return component
  }

  // 3. Root type match: {"type": "x-sre-foo", ...}
  if (data.type === componentName) return data

  // 4. Fallback: return data as-is
  return data
}
