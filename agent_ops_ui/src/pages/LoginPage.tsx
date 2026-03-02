/**
 * Full-page login with Deep Space aesthetic.
 */
import React from 'react'
import { GoogleSignInButton } from '../components/auth/GoogleSignInButton'
import { signInAsGuest } from '../services/authService'
import { useAuthStore } from '../stores/authStore'
import { colors, typography, spacing, radii, shadows } from '../theme/tokens'
import { glassCardElevated, glassButton } from '../theme/glassStyles'

export const LoginPage: React.FC = () => {
  const error = useAuthStore((s) => s.error)

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Logo / icon */}
        <div style={styles.logoContainer}>
          <div style={styles.logoIcon}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="20" stroke={colors.cyan} strokeWidth="2" />
              <path
                d="M16 28 L24 16 L32 28 L24 24 Z"
                fill={colors.cyan}
                opacity="0.8"
              />
              <circle cx="24" cy="24" r="4" fill={colors.primary} />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h1 style={styles.title}>AutoSRE</h1>
        <p style={styles.subtitle}>AI-Powered SRE Investigation</p>

        {/* Google sign in */}
        <div style={styles.section}>
          <GoogleSignInButton />
        </div>

        {/* Divider */}
        <div style={styles.divider}>
          <div style={styles.dividerLine} />
          <span style={styles.dividerText}>or</span>
          <div style={styles.dividerLine} />
        </div>

        {/* Guest mode */}
        <button
          style={styles.guestButton}
          onClick={signInAsGuest}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = colors.glassHover
            e.currentTarget.style.borderColor = colors.cyan
          }}
          onMouseLeave={(e) => {
            Object.assign(e.currentTarget.style, glassButton())
          }}
        >
          Continue as Guest
        </button>

        {/* Error area */}
        {error && (
          <div style={styles.errorBox}>
            <p style={styles.errorText}>{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    background: colors.background,
    fontFamily: typography.fontFamily,
  },
  card: {
    ...glassCardElevated({ borderRadius: radii.xl }),
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: `${spacing.xxxl + 8}px ${spacing.xxxl + 16}px`,
    width: 380,
    maxWidth: '90vw',
    gap: spacing.lg,
  },
  logoContainer: {
    marginBottom: spacing.xs,
  },
  logoIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 72,
    height: 72,
    borderRadius: '50%',
    background: `rgba(6, 182, 212, 0.1)`,
    boxShadow: shadows.glow(colors.cyan),
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.hero,
    fontWeight: typography.weights.bold,
    margin: 0,
    letterSpacing: '-0.5px',
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: typography.sizes.md,
    margin: 0,
    marginTop: -spacing.sm,
  },
  section: {
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
    marginTop: spacing.md,
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    width: '100%',
    gap: spacing.md,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    background: colors.surfaceBorder,
  },
  dividerText: {
    color: colors.textMuted,
    fontSize: typography.sizes.sm,
    textTransform: 'uppercase' as const,
    letterSpacing: '1px',
  },
  guestButton: {
    ...glassButton(),
    width: '100%',
    padding: `${spacing.md}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    fontWeight: typography.weights.medium,
  },
  errorBox: {
    width: '100%',
    padding: `${spacing.sm}px ${spacing.md}px`,
    background: colors.errorDim,
    borderRadius: radii.md,
    border: `1px solid ${colors.error}33`,
  },
  errorText: {
    color: colors.error,
    fontSize: typography.sizes.sm,
    margin: 0,
    textAlign: 'center' as const,
  },
}
