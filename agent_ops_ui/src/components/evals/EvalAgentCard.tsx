import React, { useCallback } from 'react'
import type { EvalConfig } from '../../types'
import { Settings, Trash2 } from 'lucide-react'

const METRIC_COLORS: Record<string, string> = {
  coherence: '#06B6D4',
  groundedness: '#8B5CF6',
  fluency: '#10B981',
  safety: '#F59E0B',
  relevance: '#EC4899',
  faithfulness: '#3B82F6',
}

function colorForMetric(name: string): string {
  return METRIC_COLORS[name.toLowerCase()] ?? '#94A3B8'
}

interface EvalAgentCardProps {
  config: EvalConfig
  onSelect: (agentName: string) => void
  onEdit: (config: EvalConfig) => void
  onDelete: (agentName: string) => void
}

export default function EvalAgentCard({
  config,
  onSelect,
  onEdit,
  onDelete,
}: EvalAgentCardProps) {
  const handleCardClick = useCallback(() => {
    onSelect(config.agent_name)
  }, [onSelect, config.agent_name])

  const handleEdit = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onEdit(config)
    },
    [onEdit, config],
  )

  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onDelete(config.agent_name)
    },
    [onDelete, config.agent_name],
  )

  const samplingPct = Math.round(config.sampling_rate * 100)

  return (
    <div
      style={styles.card}
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleCardClick()
        }
      }}
    >
      {/* Header: agent name + enabled badge */}
      <div style={styles.header}>
        <span style={styles.agentName}>{config.agent_name}</span>
        <span
          style={{
            ...styles.badge,
            background: config.is_enabled
              ? 'rgba(16, 185, 129, 0.15)'
              : 'rgba(100, 116, 139, 0.15)',
            color: config.is_enabled ? '#10B981' : '#64748B',
            borderColor: config.is_enabled
              ? 'rgba(16, 185, 129, 0.3)'
              : 'rgba(100, 116, 139, 0.3)',
          }}
        >
          {config.is_enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>

      {/* Metric chips */}
      <div style={styles.metricsRow}>
        {config.metrics.map((metric) => (
          <span key={metric} style={styles.metricChip}>
            <span
              style={{
                ...styles.metricDot,
                background: colorForMetric(metric),
              }}
            />
            {metric}
          </span>
        ))}
      </div>

      {/* Footer: sampling rate + actions */}
      <div style={styles.footer}>
        <span style={styles.samplingText}>
          Sampling: {samplingPct}%
        </span>
        <div style={styles.actions}>
          <button
            type="button"
            style={styles.actionButton}
            onClick={handleEdit}
            aria-label={`Edit ${config.agent_name} configuration`}
          >
            <Settings size={14} />
          </button>
          <button
            type="button"
            style={styles.actionButton}
            onClick={handleDelete}
            aria-label={`Delete ${config.agent_name} configuration`}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '16px',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    transition: 'border-color 0.2s',
    fontFamily: "'Outfit', sans-serif",
    color: '#F0F4F8',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
  },
  agentName: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#F8FAFC',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  badge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '9999px',
    border: '1px solid',
    flexShrink: 0,
  },
  metricsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  metricChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#CBD5E1',
    background: '#0F172A',
    borderRadius: '4px',
    padding: '2px 8px',
  },
  metricDot: {
    display: 'inline-block',
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTop: '1px solid #334155',
    paddingTop: '10px',
    marginTop: '2px',
  },
  samplingText: {
    fontSize: '12px',
    color: '#64748B',
  },
  actions: {
    display: 'flex',
    gap: '4px',
  },
  actionButton: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    border: '1px solid #334155',
    background: 'transparent',
    color: '#94A3B8',
    cursor: 'pointer',
    transition: 'all 0.15s',
    padding: 0,
  },
}
