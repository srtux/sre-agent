/**
 * Compact inline tool call card — shows name, status icon, duration.
 * Click to expand and view args/result JSON.
 */
import { useState } from 'react'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import type { ToolLog } from '../../types/sre'

interface Props {
  toolCall: ToolLog
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    ...glassCard(),
    padding: `${spacing.sm}px ${spacing.md}px`,
    cursor: 'pointer',
    transition: `background ${transitions.fast}`,
    fontSize: typography.sizes.sm,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
  },
  toolName: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.sm,
    color: colors.cyan,
    fontWeight: typography.weights.medium,
  },
  statusIcon: {
    fontSize: typography.sizes.md,
    lineHeight: 1,
  },
  duration: {
    marginLeft: 'auto',
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    fontFamily: typography.monoFamily,
  },
  expandedBody: {
    marginTop: spacing.sm,
    padding: spacing.sm,
    background: 'rgba(15, 23, 42, 0.5)',
    borderRadius: radii.sm,
    overflow: 'auto',
    maxHeight: 200,
  },
  jsonLabel: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: 4,
    fontWeight: typography.weights.medium,
  },
  jsonContent: {
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.xs,
    color: colors.textSecondary,
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
    lineHeight: 1.4,
  },
  section: {
    marginBottom: spacing.sm,
  },
}

function StatusIcon({ status }: { status: ToolLog['status'] }) {
  switch (status) {
    case 'running':
      return (
        <span style={{ ...styles.statusIcon, color: colors.warning }}>
          ⟳
        </span>
      )
    case 'completed':
      return (
        <span style={{ ...styles.statusIcon, color: colors.success }}>
          ✓
        </span>
      )
    case 'error':
      return (
        <span style={{ ...styles.statusIcon, color: colors.error }}>
          ✗
        </span>
      )
  }
}

function formatDuration(ms?: number): string {
  if (ms == null) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export default function ToolCallInline({ toolCall }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      style={styles.card}
      onClick={() => setExpanded((prev) => !prev)}
    >
      <div style={styles.header}>
        <StatusIcon status={toolCall.status} />
        <span style={styles.toolName}>{toolCall.toolName}</span>
        {toolCall.duration != null && (
          <span style={styles.duration}>
            {formatDuration(toolCall.duration)}
          </span>
        )}
      </div>

      {expanded && (
        <div style={styles.expandedBody}>
          {toolCall.args && Object.keys(toolCall.args).length > 0 && (
            <div style={styles.section}>
              <div style={styles.jsonLabel}>Args</div>
              <pre style={styles.jsonContent}>
                {formatJson(toolCall.args)}
              </pre>
            </div>
          )}
          {toolCall.result !== undefined && (
            <div>
              <div style={styles.jsonLabel}>Result</div>
              <pre style={styles.jsonContent}>
                {formatJson(toolCall.result)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
