import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { useAgentContext } from '../../contexts/AgentContext'
import { Cpu, Wrench, Bot, AlertCircle, Zap } from 'lucide-react'

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '16px 24px',
    background: 'rgba(2, 6, 23, 0.4)',
    borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
  },
  summaryRow: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
    alignItems: 'center',
    paddingBottom: '12px',
    borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '3px 8px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600,
  },
  metaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    color: '#94A3B8',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  heading: {
    fontSize: '11px',
    fontWeight: 700,
    color: '#F0F4F8',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  codeBlock: {
    background: '#0F172A',
    padding: '12px',
    borderRadius: '6px',
    border: '1px solid rgba(255,255,255,0.05)',
    color: '#cbd5e1',
    whiteSpace: 'pre-wrap',
    overflowX: 'auto',
    maxHeight: '300px',
    overflowY: 'auto',
    lineHeight: '1.5',
  },
  tokenBar: {
    display: 'flex',
    height: '8px',
    borderRadius: '4px',
    overflow: 'hidden',
    background: 'rgba(255,255,255,0.05)',
    maxWidth: '300px',
  },
  logRow: {
    display: 'flex',
    gap: '12px',
    padding: '6px 0',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
  },
  logTime: {
    color: '#64748B',
    whiteSpace: 'nowrap',
    minWidth: '70px',
  },
  logSev: {
    fontWeight: 600,
    width: '60px',
  },
  logSevINFO: { color: '#38BDF8' },
  logSevWARNING: { color: '#FACC15' },
  logSevERROR: { color: '#F87171' },
  logSevDEBUG: { color: '#94A3B8' },
  logPayload: {
    color: '#cbd5e1',
    wordBreak: 'break-word',
  },
}

interface ExceptionDetails {
  type: string
  message: string
  stacktrace?: string
}

interface LogEntry {
  timestamp: string | null
  severity: string
  payload: string | Record<string, unknown>
}

interface EvalEventLocal {
  metricName: string
  score: number
  explanation: string
}

interface SpanDetailsData {
  traceId: string
  spanId: string
  statusCode: string | number
  statusMessage: string
  exceptions: ExceptionDetails[]
  evaluations?: EvalEventLocal[]
  attributes: Record<string, unknown>
  logs: LogEntry[]
}

function evalScoreColor(score: number): string {
  if (score >= 0.8) return '#10B981'
  if (score >= 0.5) return '#F59E0B'
  return '#EF4444'
}

function evalScoreBg(score: number): string {
  if (score >= 0.8) return 'rgba(16, 185, 129, 0.1)'
  if (score >= 0.5) return 'rgba(245, 158, 11, 0.1)'
  return 'rgba(239, 68, 68, 0.1)'
}

function formatTokens(count: number): string {
  if (!count) return '0'
  if (count < 1000) return `${count}`
  if (count < 1000000) return `${(count / 1000).toFixed(1)}k`
  return `${(count / 1000000).toFixed(2)}M`
}

function formatJsonValue(val: unknown): string {
  if (val === null || val === undefined) return ''
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return val
    }
  }
  return JSON.stringify(val, null, 2)
}

/** Detect if this span is a GenerateContent / LLM call from its attributes. */
function detectSpanType(attrs: Record<string, unknown>): { type: 'llm' | 'tool' | 'agent' | 'unknown'; details: Record<string, unknown> } {
  const opName = String(attrs['gen_ai.operation.name'] || attrs['gcp.vertex.agent.operation'] || '')

  if (opName === 'generate_content' || opName === 'chat' || attrs['gen_ai.system'] || attrs['gen_ai.request.model']) {
    return { type: 'llm', details: attrs }
  }
  if (opName === 'execute_tool' || attrs['gen_ai.tool.name']) {
    return { type: 'tool', details: attrs }
  }
  if (opName === 'invoke_agent' || attrs['gen_ai.agent.name']) {
    return { type: 'agent', details: attrs }
  }
  return { type: 'unknown', details: attrs }
}

function SpanTypeBadge({ type }: { type: 'llm' | 'tool' | 'agent' | 'unknown' }) {
  const configs = {
    llm: { color: '#A78BFA', bg: 'rgba(167, 139, 250, 0.15)', label: 'LLM Call', icon: <Cpu size={11} /> },
    tool: { color: '#34D399', bg: 'rgba(52, 211, 153, 0.15)', label: 'Tool Call', icon: <Wrench size={11} /> },
    agent: { color: '#38BDF8', bg: 'rgba(56, 189, 248, 0.15)', label: 'Agent', icon: <Bot size={11} /> },
    unknown: { color: '#94A3B8', bg: 'rgba(148, 163, 184, 0.15)', label: 'Span', icon: null },
  }
  const cfg = configs[type]
  return (
    <span style={{ ...styles.badge, color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}33` }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

export default function SpanDetailsView({ traceId, spanId }: { traceId: string; spanId: string }) {
  const { projectId } = useAgentContext()
  const [details, setDetails] = useState<SpanDetailsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)

    axios
      .get(`/api/v1/graph/trace/${traceId}/span/${spanId}/details`, {
        params: { project_id: projectId },
      })
      .then((res) => {
        if (active) {
          setDetails(res.data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.response?.data?.detail || err.message)
          setLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [projectId, traceId, spanId])

  if (loading) {
    return <div style={{ ...styles.container, color: '#94A3B8' }}>Loading span details...</div>
  }

  if (error) {
    return <div style={{ ...styles.container, color: '#F87171' }}>Failed to load span details: {error}</div>
  }

  if (!details) return null

  const hasLogs = details.logs && details.logs.length > 0
  const hasExceptions = details.exceptions && details.exceptions.length > 0
  const hasEvals = details.evaluations && details.evaluations.length > 0
  const attrs = details.attributes || {}
  const { type: spanType } = detectSpanType(attrs)

  // Extract useful fields from attributes
  const modelName = String(attrs['gen_ai.request.model'] || attrs['gen_ai.response.model'] || '')
  const inputTokens = Number(attrs['gen_ai.usage.input_tokens'] || 0)
  const outputTokens = Number(attrs['gen_ai.usage.output_tokens'] || 0)
  const totalTokens = inputTokens + outputTokens
  const toolName = String(attrs['gen_ai.tool.name'] || '')
  const agentName = String(attrs['gen_ai.agent.name'] || '')
  const finishReasons = attrs['gen_ai.response.finish_reasons']
    ? String(attrs['gen_ai.response.finish_reasons'])
    : null

  // Extract prompt/completion from attributes (GenerateContent spans)
  const prompt = (attrs['gen_ai.prompt'] || attrs['gen_ai.request.message'] || attrs['gcp.vertex.agent.llm_request'] || null) as string | null
  const completion = (attrs['gen_ai.completion'] || attrs['gen_ai.response.message'] || attrs['gcp.vertex.agent.llm_response'] || null) as string | null
  const toolInput = (attrs['tool.input'] || attrs['gen_ai.tool.input'] || attrs['gcp.vertex.agent.tool_call_args'] || null) as string | null
  const toolOutput = (attrs['tool.output'] || attrs['gen_ai.tool.output'] || attrs['gcp.vertex.agent.tool_response'] || null) as string | null

  const isError = String(details.statusCode) === '2'

  // Filter out extracted attributes for the "Other Attributes" section
  const knownKeys = new Set([
    'gen_ai.operation.name', 'gen_ai.system', 'gen_ai.request.model', 'gen_ai.response.model',
    'gen_ai.usage.input_tokens', 'gen_ai.usage.output_tokens', 'gen_ai.response.finish_reasons',
    'gen_ai.tool.name', 'gen_ai.agent.name', 'gen_ai.prompt', 'gen_ai.completion',
    'gen_ai.request.message', 'gen_ai.response.message', 'gcp.vertex.agent.llm_request',
    'gcp.vertex.agent.llm_response', 'tool.input', 'tool.output', 'gen_ai.tool.input',
    'gen_ai.tool.output', 'gcp.vertex.agent.tool_call_args', 'gcp.vertex.agent.tool_response',
    'gen_ai.system.message', 'gcp.vertex.agent.operation', 'gen_ai.agent.id', 'gen_ai.tool.call.id',
    'tool_input', 'tool_output',
  ])
  const otherAttrs: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(attrs)) {
    if (!knownKeys.has(k)) otherAttrs[k] = v
  }
  const hasOtherAttrs = Object.keys(otherAttrs).length > 0

  return (
    <div style={styles.container}>
      {/* Summary row */}
      <div style={styles.summaryRow}>
        <SpanTypeBadge type={spanType} />

        {modelName && (
          <span style={{ ...styles.badge, color: '#A78BFA', background: 'rgba(167, 139, 250, 0.1)', border: '1px solid rgba(167, 139, 250, 0.2)' }}>
            {modelName.replace('models/', '')}
          </span>
        )}

        {toolName && (
          <span style={{ ...styles.badge, color: '#34D399', background: 'rgba(52, 211, 153, 0.1)', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
            {toolName}
          </span>
        )}

        {agentName && (
          <span style={styles.metaItem}>
            Agent: <span style={{ color: '#38BDF8' }}>{agentName}</span>
          </span>
        )}

        {isError && (
          <span style={{ ...styles.badge, color: '#F87171', background: 'rgba(248, 113, 113, 0.1)', border: '1px solid rgba(248, 113, 113, 0.2)' }}>
            <AlertCircle size={11} /> Error
          </span>
        )}

        {finishReasons && (
          <span style={styles.metaItem}>
            Finish: <span style={{ color: '#F0F4F8' }}>{finishReasons}</span>
          </span>
        )}

        {details.statusMessage && (
          <span style={{ ...styles.metaItem, color: isError ? '#F87171' : '#94A3B8' }}>
            {details.statusMessage}
          </span>
        )}
      </div>

      {/* Token usage for LLM spans */}
      {totalTokens > 0 && (
        <div style={styles.section}>
          <div style={styles.heading}>
            <Zap size={12} color="#FACC15" /> Token Usage
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={styles.tokenBar}>
              <div
                style={{
                  width: `${totalTokens > 0 ? (inputTokens / totalTokens) * 100 : 50}%`,
                  background: '#818CF8',
                  borderRadius: '4px 0 0 4px',
                }}
              />
              <div
                style={{
                  flex: 1,
                  background: '#34D399',
                  borderRadius: '0 4px 4px 0',
                }}
              />
            </div>
            <span style={{ fontSize: '11px', color: '#818CF8' }}>
              {formatTokens(inputTokens)} input
            </span>
            <span style={{ fontSize: '11px', color: '#34D399' }}>
              {formatTokens(outputTokens)} output
            </span>
            <span style={{ fontSize: '11px', color: '#64748B' }}>
              ({formatTokens(totalTokens)} total)
            </span>
          </div>
        </div>
      )}

      {/* Exceptions */}
      {hasExceptions && (
        <div style={styles.section}>
          <div style={{ ...styles.heading, color: '#F87171' }}>
            <AlertCircle size={12} /> Exceptions ({details.exceptions.length})
          </div>
          {details.exceptions.map((exc, i) => (
            <div key={i} style={{ ...styles.codeBlock, borderColor: 'rgba(248, 113, 113, 0.2)' }}>
              <strong style={{ color: '#F87171' }}>{exc.type}:</strong> {exc.message}
              {exc.stacktrace && `\n\n${exc.stacktrace}`}
            </div>
          ))}
        </div>
      )}

      {/* Prompt / LLM Input */}
      {prompt && (
        <div style={styles.section}>
          <div style={styles.heading}>Prompt / Request</div>
          <div style={styles.codeBlock}>{formatJsonValue(prompt)}</div>
        </div>
      )}

      {/* Tool Input */}
      {toolInput && (
        <div style={styles.section}>
          <div style={styles.heading}>
            <Wrench size={12} color="#34D399" /> Tool Input (Arguments)
          </div>
          <div style={styles.codeBlock}>{formatJsonValue(toolInput)}</div>
        </div>
      )}

      {/* Completion / LLM Output */}
      {completion && (
        <div style={styles.section}>
          <div style={styles.heading}>Completion / Response</div>
          <div style={styles.codeBlock}>{formatJsonValue(completion)}</div>
        </div>
      )}

      {/* Tool Output */}
      {toolOutput && (
        <div style={styles.section}>
          <div style={styles.heading}>
            <Wrench size={12} color="#34D399" /> Tool Output (Result)
          </div>
          <div style={styles.codeBlock}>{formatJsonValue(toolOutput)}</div>
        </div>
      )}

      {/* Evaluations */}
      {hasEvals && (
        <div style={styles.section}>
          <div style={{ ...styles.heading, color: '#8B5CF6' }}>AI Evaluation ({details.evaluations!.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {details.evaluations!.map((ev, i) => (
              <div
                key={i}
                style={{
                  background: evalScoreBg(ev.score),
                  border: `1px solid ${evalScoreColor(ev.score)}33`,
                  borderRadius: '8px',
                  padding: '10px 14px',
                  minWidth: '160px',
                  flex: '1 1 200px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ color: '#F0F4F8', fontWeight: 600, fontSize: '12px', textTransform: 'capitalize' }}>
                    {ev.metricName}
                  </span>
                  <span
                    style={{
                      color: evalScoreColor(ev.score),
                      fontWeight: 700,
                      fontSize: '14px',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {ev.score.toFixed(2)}
                  </span>
                </div>
                {ev.explanation && (
                  <div style={{ color: '#94A3B8', fontSize: '11px', lineHeight: '1.4', marginTop: '4px' }}>
                    {ev.explanation}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Correlated Logs */}
      {hasLogs && (
        <div style={styles.section}>
          <div style={styles.heading}>Correlated Logs ({details.logs.length})</div>
          <div style={styles.codeBlock}>
            {details.logs.map((log, i) => {
              const d = log.timestamp ? new Date(log.timestamp) : null
              const timeStr = d
                ? `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
                : '-'
              const sev = log.severity || 'INFO'
              const sevStyle = styles[`logSev${sev}`] || styles.logSevINFO

              let payloadStr = ''
              if (typeof log.payload === 'string') payloadStr = log.payload
              else payloadStr = JSON.stringify(log.payload, null, 2)

              return (
                <div key={i} style={styles.logRow}>
                  <div style={styles.logTime}>{timeStr}</div>
                  <div style={{ ...styles.logSev, ...sevStyle }}>{sev}</div>
                  <div style={styles.logPayload}>{payloadStr}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Other Attributes */}
      {hasOtherAttrs && (
        <div style={styles.section}>
          <div style={styles.heading}>Span Attributes</div>
          <div style={styles.codeBlock}>{JSON.stringify(otherAttrs, null, 2)}</div>
        </div>
      )}
    </div>
  )
}
