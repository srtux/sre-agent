import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { useAgentContext } from '../../contexts/AgentContext'

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
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  heading: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#F0F4F8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '4px',
  },
  codeBlock: {
    background: '#0F172A',
    padding: '12px',
    borderRadius: '6px',
    border: '1px solid rgba(255,255,255,0.05)',
    color: '#cbd5e1',
    whiteSpace: 'pre-wrap',
    overflowX: 'auto',
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
  }
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

interface SpanDetails {
  traceId: string
  spanId: string
  statusCode: string | number
  statusMessage: string
  exceptions: ExceptionDetails[]
  attributes: Record<string, unknown>
  logs: LogEntry[]
}

export default function SpanDetailsView({ traceId, spanId }: { traceId: string, spanId: string }) {
  const { projectId } = useAgentContext()
  const [details, setDetails] = useState<SpanDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)

    const rawSpanId = spanId

    axios.get(`/api/v1/graph/trace/${traceId}/span/${rawSpanId}/details`, {
      params: { project_id: projectId }
    }).then(res => {
      if (active) {
        setDetails(res.data)
        setLoading(false)
      }
    }).catch(err => {
      if (active) {
        setError(err.response?.data?.detail || err.message)
        setLoading(false)
      }
    })

    return () => { active = false }
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

  // Format attributes simply
  const attrsStr = JSON.stringify(details.attributes, null, 2)

  return (
    <div style={styles.container}>
      {hasExceptions && (
        <div style={styles.section}>
          <div style={{ ...styles.heading, color: '#F87171' }}>Exceptions ({details.exceptions.length})</div>
          {details.exceptions.map((exc, i) => (
            <div key={i} style={styles.codeBlock}>
              <strong style={{ color: '#F87171' }}>{exc.type}:</strong> {exc.message}
              {exc.stacktrace && `\n\n${exc.stacktrace}`}
            </div>
          ))}
        </div>
      )}

      {hasLogs && (
        <div style={styles.section}>
          <div style={styles.heading}>Correlated Logs ({details.logs.length})</div>
          <div style={styles.codeBlock}>
            {details.logs.map((log, i) => {
              const d = log.timestamp ? new Date(log.timestamp) : null
              const timeStr = d ? `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}` : '-'
              const sev = log.severity || 'INFO'
              const sevStyle = styles[`logSev${sev}`] || styles.logSevINFO

              let payloadStr = ""
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

      <div style={styles.section}>
        <div style={styles.heading}>Span Attributes</div>
        <div style={styles.codeBlock}>
          {attrsStr !== '{}' ? attrsStr : 'No attributes collected.'}
        </div>
      </div>
    </div>
  )
}
