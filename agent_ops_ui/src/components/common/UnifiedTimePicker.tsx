import { useMemo } from 'react'
import { colors, spacing, radii, typography, transitions } from '../../theme/tokens'
import { glassCard, glassInput } from '../../theme/glassStyles'

interface TimeRange {
  start: Date
  end: Date
}

interface UnifiedTimePickerProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

const presets = [
  { label: '15m', minutes: 15 },
  { label: '1h', minutes: 60 },
  { label: '6h', minutes: 360 },
  { label: '24h', minutes: 1440 },
  { label: '7d', minutes: 10080 },
  { label: '30d', minutes: 43200 },
] as const

function toLocalISO(date: Date): string {
  const offset = date.getTimezoneOffset()
  const local = new Date(date.getTime() - offset * 60_000)
  return local.toISOString().slice(0, 16)
}

export default function UnifiedTimePicker({ value, onChange }: UnifiedTimePickerProps) {
  const activePreset = useMemo(() => {
    const diffMs = value.end.getTime() - value.start.getTime()
    const diffMinutes = Math.round(diffMs / 60_000)
    return presets.find((p) => p.minutes === diffMinutes)?.label ?? null
  }, [value])

  const handlePreset = (minutes: number) => {
    const end = new Date()
    const start = new Date(end.getTime() - minutes * 60_000)
    onChange({ start, end })
  }

  return (
    <div style={{ ...glassCard(), ...styles.container }}>
      <div style={styles.presets}>
        {presets.map((p) => (
          <button
            key={p.label}
            style={{
              ...styles.presetBtn,
              ...(activePreset === p.label ? styles.presetActive : {}),
            }}
            onClick={() => handlePreset(p.minutes)}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div style={styles.custom}>
        <input
          type="datetime-local"
          value={toLocalISO(value.start)}
          onChange={(e) => {
            const d = new Date(e.target.value)
            if (!isNaN(d.getTime())) onChange({ ...value, start: d })
          }}
          style={{ ...glassInput(), ...styles.input }}
        />
        <span style={styles.separator}>to</span>
        <input
          type="datetime-local"
          value={toLocalISO(value.end)}
          onChange={(e) => {
            const d = new Date(e.target.value)
            if (!isNaN(d.getTime())) onChange({ ...value, end: d })
          }}
          style={{ ...glassInput(), ...styles.input }}
        />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.md,
    padding: spacing.lg,
  },
  presets: {
    display: 'flex',
    gap: spacing.xs,
    flexWrap: 'wrap',
  },
  presetBtn: {
    background: colors.surface,
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.md,
    color: colors.textSecondary,
    padding: `${spacing.xs}px ${spacing.md}px`,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    cursor: 'pointer',
    transition: transitions.fast,
  },
  presetActive: {
    background: `${colors.cyan}22`,
    borderColor: colors.cyan,
    color: colors.cyan,
  },
  custom: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    flexWrap: 'wrap',
  },
  input: {
    padding: `${spacing.xs}px ${spacing.sm}px`,
    fontSize: typography.sizes.sm,
    flex: 1,
    minWidth: 180,
  },
  separator: {
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
  },
}
