/**
 * Segmented button group for query language selection.
 * Options: MQL, PromQL, SQL, Trace Filter.
 */
import { useDashboardStore } from '../../stores/dashboardStore'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassButton } from '../../theme/glassStyles'

const LANGUAGES = ['MQL', 'PromQL', 'SQL', 'Trace Filter'] as const
export type QueryLanguage = (typeof LANGUAGES)[number]

/** Map store index to language string. */
// eslint-disable-next-line react-refresh/only-export-components
export function languageFromIndex(index: number): QueryLanguage {
  return LANGUAGES[index] ?? 'MQL'
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'inline-flex',
    borderRadius: radii.md,
    overflow: 'hidden',
    border: `1px solid ${colors.glassBorder}`,
  },
  button: {
    ...glassButton(),
    border: 'none',
    borderRadius: 0,
    padding: `${spacing.sm}px ${spacing.md}px`,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    transition: transitions.fast,
    whiteSpace: 'nowrap',
  },
  active: {
    background: colors.cyan,
    color: '#FFFFFF',
    fontWeight: typography.weights.semibold,
  },
}

export default function QueryLanguageToggle() {
  const index = useDashboardStore((s) => s.metricsQueryLanguage)
  const setIndex = useDashboardStore((s) => s.setMetricsQueryLanguage)

  return (
    <div style={styles.container}>
      {LANGUAGES.map((lang, i) => (
        <button
          key={lang}
          type="button"
          style={{
            ...styles.button,
            ...(i === index ? styles.active : {}),
            borderRight:
              i < LANGUAGES.length - 1
                ? `1px solid ${colors.glassBorder}`
                : undefined,
          }}
          onClick={() => setIndex(i)}
        >
          {lang}
        </button>
      ))}
    </div>
  )
}
