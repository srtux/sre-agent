/**
 * Collapsible JSON viewer with syntax highlighting.
 * Uses react-syntax-highlighter with a dark theme.
 */
import { useState, useMemo } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { colors, typography, radii, spacing } from '../../theme/tokens'

interface JsonPayloadViewerProps {
  data: unknown
  maxHeight?: number
}

const COLLAPSED_LINES = 3

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    borderRadius: radii.md,
    overflow: 'hidden',
  },
  toggleBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: `${spacing.xs}px ${spacing.sm}px`,
    marginTop: spacing.xs,
    background: 'transparent',
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.sm,
    color: colors.cyan,
    fontSize: typography.sizes.xs,
    fontFamily: typography.fontFamily,
    cursor: 'pointer',
  },
  truncation: {
    color: colors.textMuted,
    fontSize: typography.sizes.xs,
    fontStyle: 'italic',
    padding: `0 ${spacing.sm}px ${spacing.xs}px`,
    background: 'rgba(15, 23, 42, 0.8)',
  },
}

const highlighterCustomStyle: React.CSSProperties = {
  margin: 0,
  padding: '8px 12px',
  borderRadius: '8px',
  fontSize: '12px',
  background: 'rgba(15, 23, 42, 0.8)',
}

export default function JsonPayloadViewer({ data, maxHeight }: JsonPayloadViewerProps) {
  const [expanded, setExpanded] = useState(false)

  const formatted = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }, [data])

  const lines = formatted.split('\n')
  const needsTruncation = lines.length > COLLAPSED_LINES
  const displayText = expanded || !needsTruncation
    ? formatted
    : lines.slice(0, COLLAPSED_LINES).join('\n')

  return (
    <div style={styles.container}>
      <div style={{ maxHeight: expanded ? (maxHeight ?? 400) : undefined, overflow: 'auto' }}>
        <SyntaxHighlighter
          language="json"
          style={vscDarkPlus}
          customStyle={highlighterCustomStyle}
          wrapLongLines
        >
          {displayText}
        </SyntaxHighlighter>
        {!expanded && needsTruncation && (
          <div style={styles.truncation}>...</div>
        )}
      </div>
      {needsTruncation && (
        <button
          style={styles.toggleBtn}
          onClick={() => setExpanded((p) => !p)}
        >
          {expanded ? '▲ Collapse' : '▼ Expand'} ({lines.length} lines)
        </button>
      )}
    </div>
  )
}
