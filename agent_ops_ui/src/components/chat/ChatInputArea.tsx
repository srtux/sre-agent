/**
 * Chat input textarea — Enter to send, Shift+Enter for newline.
 * Send button toggles to cancel button during streaming.
 * Up/Down arrows navigate prompt history.
 */
import { useState, useRef, useCallback } from 'react'
import { colors, spacing, typography } from '../../theme/tokens'
import { glassInput, primaryButton, glassButton } from '../../theme/glassStyles'
import { usePromptHistory } from '../../hooks/usePromptHistory'

interface Props {
  onSend: (text: string) => void
  onCancel: () => void
  isStreaming: boolean
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: spacing.sm,
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderTop: `1px solid ${colors.surfaceBorder}`,
    background: colors.backgroundLight,
  },
  textarea: {
    ...glassInput(),
    flex: 1,
    resize: 'none' as const,
    padding: `${spacing.md}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    lineHeight: 1.5,
    minHeight: 42,
    maxHeight: 160,
    overflow: 'auto',
  },
  sendBtn: {
    ...primaryButton(),
    padding: `${spacing.md}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 72,
    height: 42,
  },
  cancelBtn: {
    ...glassButton({
      borderColor: colors.error,
    }),
    padding: `${spacing.md}px ${spacing.lg}px`,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    color: colors.error,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 72,
    height: 42,
  },
  sendBtnDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
  },
}

export default function ChatInputArea({ onSend, onCancel, isStreaming }: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const history = usePromptHistory()

  const handleSend = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return
    history.add(trimmed)
    onSend(trimmed)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [text, isStreaming, onSend, history])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
      return
    }

    if (e.key === 'ArrowUp' && !text) {
      e.preventDefault()
      const prev = history.navigateUp()
      if (prev !== null) setText(prev)
      return
    }

    if (e.key === 'ArrowDown' && !text) {
      e.preventDefault()
      const next = history.navigateDown()
      setText(next ?? '')
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    // Auto-resize
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const canSend = text.trim().length > 0 && !isStreaming

  return (
    <div style={styles.container}>
      <textarea
        ref={textareaRef}
        style={styles.textarea}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your services..."
        rows={1}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = colors.cyan
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = colors.surfaceBorder
        }}
      />

      {isStreaming ? (
        <button style={styles.cancelBtn} onClick={onCancel}>
          Cancel
        </button>
      ) : (
        <button
          style={{
            ...styles.sendBtn,
            ...(canSend ? {} : styles.sendBtnDisabled),
          }}
          onClick={handleSend}
          disabled={!canSend}
        >
          Send
        </button>
      )}
    </div>
  )
}
