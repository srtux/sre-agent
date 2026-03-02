/**
 * Glass morphism utility functions returning React.CSSProperties.
 * Ported from AppColors/GlassDecoration in the Flutter theme.
 */
import type React from 'react'
import { colors, radii, shadows } from './tokens'

/** Standard glass card style. */
export function glassCard(overrides?: React.CSSProperties): React.CSSProperties {
  return {
    background: colors.glassBg,
    border: `1px solid ${colors.glassBorder}`,
    borderRadius: radii.lg,
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    ...overrides,
  }
}

/** Elevated glass card with shadow. */
export function glassCardElevated(overrides?: React.CSSProperties): React.CSSProperties {
  return {
    ...glassCard(),
    boxShadow: shadows.md,
    ...overrides,
  }
}

/** Glass surface for containers/panels. */
export function glassSurface(overrides?: React.CSSProperties): React.CSSProperties {
  return {
    background: colors.surface,
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.lg,
    ...overrides,
  }
}

/** Glass input field style. */
export function glassInput(overrides?: React.CSSProperties): React.CSSProperties {
  return {
    background: 'rgba(15, 23, 42, 0.6)',
    border: `1px solid ${colors.surfaceBorder}`,
    borderRadius: radii.md,
    color: colors.textPrimary,
    outline: 'none',
    transition: 'border-color 0.15s ease',
    ...overrides,
  }
}

/** Glass button style. */
export function glassButton(overrides?: React.CSSProperties): React.CSSProperties {
  return {
    background: colors.glassBg,
    border: `1px solid ${colors.glassBorder}`,
    borderRadius: radii.md,
    color: colors.textPrimary,
    cursor: 'pointer',
    transition: 'background 0.15s ease, border-color 0.15s ease',
    ...overrides,
  }
}

/** Primary action button. */
export function primaryButton(overrides?: React.CSSProperties): React.CSSProperties {
  return {
    background: `linear-gradient(135deg, ${colors.primary}, ${colors.cyan})`,
    border: 'none',
    borderRadius: radii.md,
    color: '#FFFFFF',
    cursor: 'pointer',
    fontWeight: 600,
    transition: 'opacity 0.15s ease',
    ...overrides,
  }
}

/** Status badge style based on severity. */
export function statusBadge(severity: 'success' | 'warning' | 'error' | 'info' | 'critical'): React.CSSProperties {
  const colorMap = {
    success: { bg: colors.successDim, text: colors.success },
    warning: { bg: colors.warningDim, text: colors.warning },
    error: { bg: colors.errorDim, text: colors.error },
    info: { bg: colors.infoDim, text: colors.info },
    critical: { bg: 'rgba(255, 23, 68, 0.15)', text: colors.critical },
  }
  const c = colorMap[severity]
  return {
    background: c.bg,
    color: c.text,
    padding: '2px 8px',
    borderRadius: radii.round,
    fontSize: '12px',
    fontWeight: 500,
  }
}
