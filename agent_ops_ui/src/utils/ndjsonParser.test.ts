import { describe, it, expect } from 'vitest'
import { parseNDJSONStream } from './ndjsonParser'

function createStream(text: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text))
      controller.close()
    },
  })
}

function createChunkedStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
}

async function collectEvents(stream: ReadableStream<Uint8Array>) {
  const events = []
  for await (const event of parseNDJSONStream(stream)) {
    events.push(event)
  }
  return events
}

describe('parseNDJSONStream', () => {
  it('parses single JSON line', async () => {
    const stream = createStream('{"type":"text","content":"hello"}\n')
    const events = await collectEvents(stream)
    expect(events).toHaveLength(1)
    expect(events[0]).toEqual({ type: 'text', content: 'hello' })
  })

  it('parses multiple JSON lines', async () => {
    const stream = createStream(
      '{"type":"text","content":"a"}\n{"type":"text","content":"b"}\n{"type":"text","content":"c"}\n',
    )
    const events = await collectEvents(stream)
    expect(events).toHaveLength(3)
    expect(events.map((e) => (e as { content: string }).content)).toEqual(['a', 'b', 'c'])
  })

  it('skips empty lines', async () => {
    const stream = createStream('{"type":"text","content":"a"}\n\n\n{"type":"text","content":"b"}\n')
    const events = await collectEvents(stream)
    expect(events).toHaveLength(2)
  })

  it('handles chunked data across line boundaries', async () => {
    const stream = createChunkedStream([
      '{"type":"tex',
      't","content":"split"}\n',
    ])
    const events = await collectEvents(stream)
    expect(events).toHaveLength(1)
    expect(events[0]).toEqual({ type: 'text', content: 'split' })
  })

  it('handles data without trailing newline', async () => {
    const stream = createStream('{"type":"text","content":"no-newline"}')
    const events = await collectEvents(stream)
    expect(events).toHaveLength(1)
  })

  it('skips invalid JSON lines gracefully', async () => {
    const stream = createStream(
      '{"type":"text","content":"valid"}\nnot-json\n{"type":"text","content":"also-valid"}\n',
    )
    const events = await collectEvents(stream)
    expect(events).toHaveLength(2)
  })

  it('handles empty stream', async () => {
    const stream = createStream('')
    const events = await collectEvents(stream)
    expect(events).toHaveLength(0)
  })

  it('parses various event types', async () => {
    const lines = [
      '{"type":"text","content":"hello"}',
      '{"type":"error","error":"oops"}',
      '{"type":"tool_call","tool_name":"get_traces","call_id":"c1"}',
      '{"type":"dashboard","category":"traces","widget_type":"x-sre-trace-waterfall","tool_name":"get_traces","data":{}}',
      '{"type":"session","session_id":"s1"}',
      '{"type":"suggestions","suggestions":["a","b"]}',
    ]
    const stream = createStream(lines.join('\n') + '\n')
    const events = await collectEvents(stream)
    expect(events).toHaveLength(6)
    expect(events.map((e) => e.type)).toEqual([
      'text', 'error', 'tool_call', 'dashboard', 'session', 'suggestions',
    ])
  })
})
