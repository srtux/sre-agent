/**
 * NDJSON (Newline-Delimited JSON) stream parser.
 * Async generator that yields parsed objects from a ReadableStream.
 * Ported from autosre/lib/agent/adk_content_generator.dart
 */
import type { StreamEvent } from '../types/streaming'

/**
 * Parse a ReadableStream of NDJSON into an async generator of StreamEvents.
 * Each line is expected to be a valid JSON object.
 */
export async function* parseNDJSONStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<StreamEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // Keep the last partial line in the buffer
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        try {
          yield JSON.parse(trimmed) as StreamEvent
        } catch {
          console.warn('[NDJSON] Failed to parse line:', trimmed.slice(0, 200))
        }
      }
    }

    // Process any remaining content in buffer
    const remaining = buffer.trim()
    if (remaining) {
      try {
        yield JSON.parse(remaining) as StreamEvent
      } catch {
        console.warn('[NDJSON] Failed to parse remaining buffer:', remaining.slice(0, 200))
      }
    }
  } finally {
    reader.releaseLock()
  }
}
