/**
 * Dropdown overlay showing keyword suggestions based on query language.
 * Filters keywords by current input and inserts on click.
 */
import { useMemo } from 'react'
import { colors, radii, spacing, typography, zIndex, shadows } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const KEYWORDS: Record<string, string[]> = {
  MQL: ['fetch', 'rate', 'sum', 'align', 'every', 'resource.type', 'metric.type'],
  PromQL: ['rate', 'sum', 'avg', 'histogram_quantile', 'increase'],
  SQL: ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'JOIN', 'LIMIT'],
  'Trace Filter': ['service.name', 'span.name', 'duration', 'status'],
}

interface QueryAutocompleteProps {
  query: string
  language: string
  onSelect: (keyword: string) => void
  visible: boolean
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    ...glassCard(),
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    marginTop: 4,
    maxHeight: 220,
    overflowY: 'auto',
    zIndex: zIndex.dropdown,
    boxShadow: shadows.lg,
    padding: spacing.xs,
  },
  item: {
    display: 'block',
    width: '100%',
    padding: `${spacing.sm}px ${spacing.md}px`,
    background: 'transparent',
    border: 'none',
    color: colors.textPrimary,
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.sm,
    textAlign: 'left',
    cursor: 'pointer',
    borderRadius: radii.sm,
    transition: 'background 0.12s ease',
  },
}

export default function QueryAutocomplete({
  query,
  language,
  onSelect,
  visible,
}: QueryAutocompleteProps) {
  const filtered = useMemo(() => {
    const all = KEYWORDS[language] || []
    if (!query.trim()) return all
    // Match against the last "word" the user is typing
    const lastWord = query.split(/[\s,(]+/).pop()?.toLowerCase() ?? ''
    if (!lastWord) return all
    return all.filter((kw) => kw.toLowerCase().startsWith(lastWord))
  }, [query, language])

  if (!visible || filtered.length === 0) return null

  return (
    <div style={styles.overlay}>
      {filtered.map((kw) => (
        <button
          key={kw}
          type="button"
          style={styles.item}
          onMouseDown={(e) => {
            e.preventDefault() // Prevent blur before click fires
            onSelect(kw)
          }}
          onMouseEnter={(e) => {
            ;(e.currentTarget as HTMLElement).style.background =
              colors.cardHover
          }}
          onMouseLeave={(e) => {
            ;(e.currentTarget as HTMLElement).style.background = 'transparent'
          }}
        >
          {kw}
        </button>
      ))}
    </div>
  )
}
