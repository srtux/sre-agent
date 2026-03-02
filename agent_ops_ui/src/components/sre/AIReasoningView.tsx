import { useState, useEffect } from 'react'
import { colors, typography, spacing, radii } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

interface ReasoningData {
  steps: Array<{ title: string; content: string }>
  conclusion: string
}

export default function AIReasoningView({ data }: { data: ReasoningData }) {
  const [revealedCount, setRevealedCount] = useState(0)

  useEffect(() => {
    if (revealedCount < data.steps.length) {
      const timer = setTimeout(() => setRevealedCount((c) => c + 1), 200)
      return () => clearTimeout(timer)
    }
  }, [revealedCount, data.steps.length])

  return (
    <div style={{ ...glassCard(), padding: spacing.lg }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.md }}>
        {data.steps.map((step, i) => {
          const visible = i < revealedCount
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: spacing.md,
                opacity: visible ? 1 : 0,
                transform: visible ? 'translateY(0)' : 'translateY(8px)',
                transition: 'opacity 0.3s ease, transform 0.3s ease',
              }}
            >
              <div style={numberBadgeStyle}>{i + 1}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: colors.textPrimary, fontSize: typography.sizes.md, marginBottom: 2 }}>
                  {step.title}
                </div>
                <div style={{ color: colors.textSecondary, fontSize: typography.sizes.sm, lineHeight: 1.5 }}>
                  {step.content}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Conclusion */}
      {revealedCount >= data.steps.length && (
        <div
          style={{
            marginTop: spacing.lg,
            padding: spacing.md,
            background: `linear-gradient(135deg, ${colors.primary}15, ${colors.cyan}15)`,
            border: `1px solid ${colors.primary}40`,
            borderRadius: radii.md,
            opacity: 1,
            transition: 'opacity 0.4s ease',
          }}
        >
          <div style={{ fontSize: typography.sizes.xs, color: colors.primary, fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Conclusion
          </div>
          <div style={{ color: colors.textPrimary, fontSize: typography.sizes.md, lineHeight: 1.5 }}>
            {data.conclusion}
          </div>
        </div>
      )}
    </div>
  )
}

const numberBadgeStyle: React.CSSProperties = {
  width: 28,
  height: 28,
  borderRadius: '50%',
  background: `linear-gradient(135deg, ${colors.primary}, ${colors.cyan})`,
  color: '#fff',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  fontSize: typography.sizes.sm,
  flexShrink: 0,
}
