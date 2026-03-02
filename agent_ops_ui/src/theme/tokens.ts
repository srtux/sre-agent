/**
 * Centralized design tokens for the Deep Space aesthetic.
 * Ported from autosre/lib/theme/app_theme.dart
 */

export const colors = {
  // Primary palette
  primary: '#6366F1',
  primaryLight: '#818CF8',
  primaryDark: '#4F46E5',
  cyan: '#06B6D4',
  cyanLight: '#22D3EE',
  blue: '#3B82F6',
  purple: '#A855F7',

  // Background
  background: '#0F172A',
  backgroundLight: '#131C2E',
  surface: '#1E293B',
  surfaceLight: '#334155',
  surfaceBorder: '#334155',
  card: '#1E293B',
  cardHover: '#263548',

  // Status
  success: '#00E676',
  successDim: 'rgba(0, 230, 118, 0.15)',
  warning: '#FFAB00',
  warningDim: 'rgba(255, 171, 0, 0.15)',
  error: '#FF5252',
  errorDim: 'rgba(255, 82, 82, 0.08)',
  info: '#29B6F6',
  infoDim: 'rgba(41, 182, 246, 0.15)',
  critical: '#FF1744',

  // Text
  textPrimary: '#F0F4F8',
  textSecondary: '#B0BEC5',
  textMuted: '#78909C',
  textDisabled: '#546E7A',

  // Severity colors
  severityDefault: '#78909C',
  severityDebug: '#78909C',
  severityInfo: '#29B6F6',
  severityWarning: '#FFAB00',
  severityError: '#FF5252',
  severityCritical: '#FF1744',

  // Agent trace operation colors
  agentInvocation: '#06B6D4',
  llmCall: '#A855F7',
  toolExecution: '#FFAB00',
  subAgentDelegation: '#22D3EE',

  // Glass morphism
  glassBg: 'rgba(30, 41, 59, 0.7)',
  glassBorder: 'rgba(51, 65, 85, 0.5)',
  glassHover: 'rgba(30, 41, 59, 0.9)',
} as const

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const

export const radii = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  round: 9999,
} as const

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  md: '0 4px 6px rgba(0, 0, 0, 0.3)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.3)',
  glow: (color: string) => `0 0 20px ${color}40`,
} as const

export const typography = {
  fontFamily: "'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  monoFamily: "'JetBrains Mono', 'Fira Code', monospace",
  sizes: {
    xs: '11px',
    sm: '12px',
    md: '14px',
    lg: '16px',
    xl: '18px',
    xxl: '20px',
    title: '24px',
    hero: '32px',
  },
  weights: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const

export const transitions = {
  fast: '0.15s ease',
  normal: '0.2s ease',
  slow: '0.3s ease',
} as const

export const zIndex = {
  dropdown: 1000,
  sticky: 1100,
  modal: 1200,
  popover: 1300,
  toast: 1400,
  tooltip: 1500,
} as const
