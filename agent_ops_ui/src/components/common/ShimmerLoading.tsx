import { colors, radii } from '../../theme/tokens'

interface ShimmerLoadingProps {
  width?: string | number
  height?: string | number
  borderRadius?: number
}

export default function ShimmerLoading({
  width = '100%',
  height = 20,
  borderRadius = radii.md,
}: ShimmerLoadingProps) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius,
        background: colors.surface,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div style={styles.shimmer} />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  shimmer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `linear-gradient(
      90deg,
      transparent 0%,
      rgba(255, 255, 255, 0.04) 50%,
      transparent 100%
    )`,
    animation: 'shimmerSweep 1.5s ease-in-out infinite',
  },
}

// Inject keyframe animation
if (typeof document !== 'undefined') {
  const id = 'shimmer-keyframes'
  if (!document.getElementById(id)) {
    const styleEl = document.createElement('style')
    styleEl.id = id
    styleEl.textContent = `
      @keyframes shimmerSweep {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
      }
    `
    document.head.appendChild(styleEl)
  }
}
