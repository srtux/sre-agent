/**
 * Horizontal row of glass-morphism suggestion chips.
 * Cyan border on hover, calls onSelect with chip text.
 */
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassButton } from '../../theme/glassStyles'

interface Props {
  suggestions: string[]
  onSelect: (text: string) => void
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: spacing.sm,
    padding: `${spacing.sm}px ${spacing.lg}px`,
    justifyContent: 'center',
  },
  chip: {
    ...glassButton(),
    padding: `${spacing.sm}px ${spacing.md}px`,
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    color: colors.textSecondary,
    borderRadius: radii.round,
    whiteSpace: 'nowrap' as const,
    transition: `border-color ${transitions.fast}, color ${transitions.fast}`,
  },
}

export default function SuggestionChips({ suggestions, onSelect }: Props) {
  return (
    <div style={styles.container}>
      {suggestions.map((text) => (
        <button
          key={text}
          style={styles.chip}
          onClick={() => onSelect(text)}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = colors.cyan
            e.currentTarget.style.color = colors.cyan
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = colors.glassBorder
            e.currentTarget.style.color = colors.textSecondary
          }}
        >
          {text}
        </button>
      ))}
    </div>
  )
}
