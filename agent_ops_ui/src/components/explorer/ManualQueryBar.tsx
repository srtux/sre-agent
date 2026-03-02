/**
 * Multi-language query input bar.
 * Top row: QueryLanguageToggle + Templates dropdown.
 * Main: textarea for query input.
 * Bottom: Execute + Clear buttons.
 */
import { useState, useCallback, useRef } from 'react'
import { Play, Trash2, BookOpen } from 'lucide-react'
import { useDashboardStore } from '../../stores/dashboardStore'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassCard, glassInput, primaryButton, glassButton } from '../../theme/glassStyles'
import QueryLanguageToggle, { languageFromIndex } from './QueryLanguageToggle'
import QueryAutocomplete from './QueryAutocomplete'

interface ManualQueryBarProps {
  onExecute: (query: string, language: string) => void
}

const TEMPLATES: Record<string, Array<{ label: string; query: string }>> = {
  MQL: [
    { label: 'CPU utilization', query: 'fetch gce_instance\n| metric compute.googleapis.com/instance/cpu/utilization\n| every 1m' },
    { label: 'Request count', query: 'fetch https_lb_rule\n| metric loadbalancing.googleapis.com/https/request_count\n| align rate(1m)\n| every 1m' },
  ],
  PromQL: [
    { label: 'Request rate', query: 'rate(http_requests_total[5m])' },
    { label: 'Error ratio', query: 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))' },
  ],
  SQL: [
    { label: 'Top spans by duration', query: 'SELECT span_name, AVG(duration_ms) as avg_dur\nFROM otel_traces.spans\nGROUP BY span_name\nORDER BY avg_dur DESC\nLIMIT 20' },
    { label: 'Error count by service', query: 'SELECT service_name, COUNT(*) as errors\nFROM otel_traces.spans\nWHERE status = "ERROR"\nGROUP BY service_name\nORDER BY errors DESC' },
  ],
  'Trace Filter': [
    { label: 'Slow spans', query: 'duration > 1000ms' },
    { label: 'Error spans', query: 'status = ERROR AND service.name = "api-server"' },
  ],
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...glassCard(),
    padding: spacing.lg,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.md,
  },
  topRow: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.md,
    flexWrap: 'wrap',
  },
  textareaWrapper: {
    position: 'relative',
  },
  textarea: {
    ...glassInput(),
    width: '100%',
    minHeight: 100,
    padding: spacing.md,
    fontFamily: typography.monoFamily,
    fontSize: typography.sizes.md,
    resize: 'vertical',
    lineHeight: 1.5,
    boxSizing: 'border-box',
  },
  bottomRow: {
    display: 'flex',
    gap: spacing.sm,
    justifyContent: 'flex-end',
  },
  executeBtn: {
    ...primaryButton(),
    display: 'inline-flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.sm}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
  },
  clearBtn: {
    ...glassButton(),
    display: 'inline-flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.sm}px ${spacing.md}px`,
    fontSize: typography.sizes.md,
  },
  templateBtn: {
    ...glassButton(),
    display: 'inline-flex',
    alignItems: 'center',
    gap: spacing.xs,
    padding: `${spacing.sm}px ${spacing.md}px`,
    fontSize: typography.sizes.sm,
    position: 'relative',
  },
  templateDropdown: {
    ...glassCard(),
    position: 'absolute',
    top: '100%',
    left: 0,
    marginTop: 4,
    minWidth: 240,
    zIndex: 1000,
    padding: spacing.xs,
  },
  templateItem: {
    display: 'block',
    width: '100%',
    padding: `${spacing.sm}px ${spacing.md}px`,
    background: 'transparent',
    border: 'none',
    color: colors.textPrimary,
    fontSize: typography.sizes.sm,
    textAlign: 'left',
    cursor: 'pointer',
    borderRadius: radii.sm,
    transition: transitions.fast,
  },
}

export default function ManualQueryBar({ onExecute }: ManualQueryBarProps) {
  const [query, setQuery] = useState('')
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [showTemplates, setShowTemplates] = useState(false)
  const langIndex = useDashboardStore((s) => s.metricsQueryLanguage)
  const language = languageFromIndex(langIndex)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleExecute = useCallback(() => {
    if (query.trim()) {
      onExecute(query.trim(), language)
    }
  }, [query, language, onExecute])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        handleExecute()
      }
    },
    [handleExecute],
  )

  const handleAutocompleteSelect = useCallback((keyword: string) => {
    setQuery((prev) => {
      // Replace the last partial word with the selected keyword
      const parts = prev.split(/(\s+)/)
      parts[parts.length - 1] = keyword
      return parts.join('') + ' '
    })
    setShowAutocomplete(false)
    textareaRef.current?.focus()
  }, [])

  const templates = TEMPLATES[language] || []

  return (
    <div style={styles.container}>
      {/* Top row: language toggle + templates */}
      <div style={styles.topRow}>
        <QueryLanguageToggle />
        {templates.length > 0 && (
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              style={styles.templateBtn}
              onClick={() => setShowTemplates((v) => !v)}
              onBlur={() => setTimeout(() => setShowTemplates(false), 150)}
            >
              <BookOpen size={14} />
              Templates
            </button>
            {showTemplates && (
              <div style={styles.templateDropdown}>
                {templates.map((t) => (
                  <button
                    key={t.label}
                    type="button"
                    style={styles.templateItem}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      setQuery(t.query)
                      setShowTemplates(false)
                    }}
                    onMouseEnter={(e) => {
                      ;(e.currentTarget as HTMLElement).style.background =
                        colors.cardHover
                    }}
                    onMouseLeave={(e) => {
                      ;(e.currentTarget as HTMLElement).style.background =
                        'transparent'
                    }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Textarea with autocomplete */}
      <div style={styles.textareaWrapper}>
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setShowAutocomplete(true)}
          onBlur={() => setTimeout(() => setShowAutocomplete(false), 150)}
          onKeyDown={handleKeyDown}
          placeholder={`Enter ${language} query... (Ctrl+Enter to execute)`}
          style={styles.textarea}
        />
        <QueryAutocomplete
          query={query}
          language={language}
          visible={showAutocomplete && query.length > 0}
          onSelect={handleAutocompleteSelect}
        />
      </div>

      {/* Bottom row: Execute + Clear */}
      <div style={styles.bottomRow}>
        <button
          type="button"
          style={styles.clearBtn}
          onClick={() => setQuery('')}
        >
          <Trash2 size={14} />
          Clear
        </button>
        <button
          type="button"
          style={styles.executeBtn}
          onClick={handleExecute}
        >
          <Play size={14} />
          Execute
        </button>
      </div>
    </div>
  )
}
