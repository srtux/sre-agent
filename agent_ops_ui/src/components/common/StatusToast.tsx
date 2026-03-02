import { useState, useCallback, useEffect, useRef } from 'react'
import { colors, spacing, radii, typography, zIndex, transitions } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'

type ToastType = 'success' | 'warning' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

// Module-level state so any component can push toasts
let listeners: Array<(toast: Toast) => void> = []
let nextId = 1

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const show = useCallback((message: string, type: ToastType = 'info') => {
    const toast: Toast = { id: nextId++, message, type }
    listeners.forEach((fn) => fn(toast))
  }, [])

  return { show }
}

const iconMap: Record<ToastType, string> = {
  success: '\u2713',
  warning: '\u26A0',
  error: '\u2717',
  info: '\u2139',
}

const colorMap: Record<ToastType, string> = {
  success: colors.success,
  warning: colors.warning,
  error: colors.error,
  info: colors.info,
}

const bgMap: Record<ToastType, string> = {
  success: colors.successDim,
  warning: colors.warningDim,
  error: colors.errorDim,
  info: colors.infoDim,
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  useEffect(() => {
    const handler = (toast: Toast) => {
      setToasts((prev) => [...prev, toast])
      const timer = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id))
        timersRef.current.delete(toast.id)
      }, 5000)
      timersRef.current.set(toast.id, timer)
    }
    listeners.push(handler)
    const timers = timersRef.current
    return () => {
      listeners = listeners.filter((fn) => fn !== handler)
      timers.forEach((timer) => clearTimeout(timer))
    }
  }, [])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
    const timer = timersRef.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timersRef.current.delete(id)
    }
  }, [])

  if (toasts.length === 0) return null

  return (
    <div style={styles.container}>
      {toasts.map((toast) => (
        <div
          key={toast.id}
          style={{
            ...glassCard(),
            ...styles.toast,
            borderLeft: `3px solid ${colorMap[toast.type]}`,
            background: bgMap[toast.type],
          }}
        >
          <span style={{ ...styles.icon, color: colorMap[toast.type] }}>
            {iconMap[toast.type]}
          </span>
          <span style={styles.message}>{toast.message}</span>
          <button
            style={styles.close}
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss"
          >
            \u00D7
          </button>
        </div>
      ))}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'fixed',
    bottom: spacing.xl,
    right: spacing.xl,
    zIndex: zIndex.toast,
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
    maxWidth: 380,
  },
  toast: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderRadius: radii.md,
    animation: 'toastSlideIn 0.2s ease',
  },
  icon: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.bold,
    flexShrink: 0,
  },
  message: {
    flex: 1,
    fontSize: typography.sizes.md,
    color: colors.textPrimary,
  },
  close: {
    background: 'none',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    fontSize: typography.sizes.lg,
    padding: spacing.xs,
    lineHeight: 1,
    transition: transitions.fast,
    flexShrink: 0,
  },
}

// Inject keyframe animation
if (typeof document !== 'undefined') {
  const styleEl = document.createElement('style')
  styleEl.textContent = `
    @keyframes toastSlideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
  `
  document.head.appendChild(styleEl)
}
