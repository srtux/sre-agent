/**
 * Floating toast notification for memory events.
 * Fixed bottom-right, auto-dismisses after 4 seconds.
 */
import { useState, useEffect, useCallback } from 'react'
import { colors, spacing, typography, zIndex } from '../../theme/tokens'
import { glassCardElevated } from '../../theme/glassStyles'
import type { MemoryEvent } from '../../types/streaming'

interface Toast {
  id: number
  action: MemoryEvent['action']
  title: string
}

let toastCounter = 0

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'fixed',
    bottom: spacing.xl,
    right: spacing.xl,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
    zIndex: zIndex.toast,
    pointerEvents: 'none',
  },
  toast: {
    ...glassCardElevated(),
    padding: `${spacing.md}px ${spacing.lg}px`,
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    pointerEvents: 'auto',
    minWidth: 220,
    animation: 'sre-toast-slide 0.3s ease-out',
  },
  icon: {
    fontSize: typography.sizes.lg,
    lineHeight: 1,
  },
  text: {
    fontSize: typography.sizes.sm,
    fontFamily: typography.fontFamily,
    color: colors.textPrimary,
  },
  action: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    textTransform: 'capitalize' as const,
  },
}

const ACTION_ICONS: Record<string, string> = {
  created: '🧠',
  updated: '📝',
  deleted: '🗑️',
}

const ACTION_COLORS: Record<string, string> = {
  created: colors.success,
  updated: colors.info,
  deleted: colors.warning,
}

// Inject keyframes
if (typeof document !== 'undefined' && !document.getElementById('sre-toast-slide')) {
  const style = document.createElement('style')
  style.id = 'sre-toast-slide'
  style.textContent = `
    @keyframes sre-toast-slide {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  `
  document.head.appendChild(style)
}

/**
 * MemoryToast component. Call showMemoryToast() to display a toast.
 * This is a singleton component — mount once at the app root.
 */

// Global listener so external code can trigger toasts
type ToastListener = (event: MemoryEvent) => void
let globalListener: ToastListener | null = null

// eslint-disable-next-line react-refresh/only-export-components
export function showMemoryToast(event: MemoryEvent): void {
  globalListener?.(event)
}

export default function MemoryToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((event: MemoryEvent) => {
    const id = ++toastCounter
    setToasts((prev) => [
      ...prev,
      {
        id,
        action: event.action,
        title: event.title ?? event.key ?? 'Memory',
      },
    ])

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  useEffect(() => {
    globalListener = addToast
    return () => {
      globalListener = null
    }
  }, [addToast])

  if (toasts.length === 0) return null

  return (
    <div style={styles.container}>
      {toasts.map((toast) => (
        <div
          key={toast.id}
          style={{
            ...styles.toast,
            borderColor: ACTION_COLORS[toast.action] ?? colors.glassBorder,
          }}
        >
          <span style={styles.icon}>
            {ACTION_ICONS[toast.action] ?? '💡'}
          </span>
          <div>
            <div style={styles.text}>{toast.title}</div>
            <div style={styles.action}>{toast.action}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
