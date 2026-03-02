/**
 * Fixed-top banner shown when the backend is unreachable.
 */
import React from 'react'
import { useConnectivity } from '../../services/connectivityService'
import { colors, typography, spacing, zIndex } from '../../theme/tokens'

export const ConnectivityBanner: React.FC = () => {
  const { isConnected } = useConnectivity()

  if (isConnected) return null

  return (
    <div style={styles.banner}>
      <span style={styles.dot} />
      <span style={styles.text}>Connection lost. Retrying...</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  banner: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: zIndex.toast,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    padding: `${spacing.sm}px ${spacing.lg}px`,
    background: `${colors.error}E6`,
    backdropFilter: 'blur(8px)',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#fff',
    opacity: 0.8,
  },
  text: {
    color: '#fff',
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    fontWeight: typography.weights.medium,
  },
}
