/**
 * Three-dot typing indicator with CSS pulse animation.
 */
import { useEffect, useRef } from 'react'
import { colors, spacing, radii } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

const DOT_SIZE = 6
const ANIMATION_NAME = 'sre-typing-pulse'

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...glassCard(),
    display: 'inline-flex',
    alignItems: 'center',
    gap: spacing.xs,
    padding: `${spacing.sm}px ${spacing.md}px`,
    borderRadius: `${radii.lg}px ${radii.lg}px ${radii.lg}px 4px`,
  },
  dot: {
    width: DOT_SIZE,
    height: DOT_SIZE,
    borderRadius: '50%',
    background: colors.cyan,
    opacity: 0.4,
  },
}

const keyframesCSS = `
@keyframes ${ANIMATION_NAME} {
  0%, 80%, 100% { opacity: 0.4; transform: scale(1); }
  40% { opacity: 1; transform: scale(1.2); }
}
`

export default function TypingIndicator() {
  const styleRef = useRef<HTMLStyleElement | null>(null)

  useEffect(() => {
    // Inject keyframes once
    if (!document.getElementById(ANIMATION_NAME)) {
      const style = document.createElement('style')
      style.id = ANIMATION_NAME
      style.textContent = keyframesCSS
      document.head.appendChild(style)
      styleRef.current = style
    }
    return () => {
      styleRef.current?.remove()
    }
  }, [])

  return (
    <div style={styles.container}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            ...styles.dot,
            animation: `${ANIMATION_NAME} 1.4s infinite ease-in-out both`,
            animationDelay: `${i * 0.16}s`,
          }}
        />
      ))}
    </div>
  )
}
