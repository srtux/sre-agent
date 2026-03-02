/**
 * Auth guard wrapper.
 * Shows children if authenticated, loading spinner if loading, LoginPage otherwise.
 */
import React from 'react'
import { useAuth } from '../../hooks/useAuth'
import { LoginPage } from '../../pages/LoginPage'
import { colors, typography } from '../../theme/tokens'

interface AuthGuardProps {
  children: React.ReactNode
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.spinner} />
        <p style={styles.loadingText}>Loading...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage />
  }

  return <>{children}</>
}

const spinnerKeyframes = `
@keyframes auth-spin {
  to { transform: rotate(360deg); }
}
`

// Inject keyframes once
if (typeof document !== 'undefined') {
  const styleEl = document.createElement('style')
  styleEl.textContent = spinnerKeyframes
  document.head.appendChild(styleEl)
}

const styles: Record<string, React.CSSProperties> = {
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: colors.background,
    gap: 16,
  },
  spinner: {
    width: 32,
    height: 32,
    border: `3px solid ${colors.surfaceBorder}`,
    borderTopColor: colors.cyan,
    borderRadius: '50%',
    animation: 'auth-spin 0.8s linear infinite',
  },
  loadingText: {
    color: colors.textSecondary,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    margin: 0,
  },
}
