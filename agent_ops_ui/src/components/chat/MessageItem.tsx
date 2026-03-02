/**
 * Chat message bubble — user messages right-aligned with gradient,
 * assistant messages left-aligned with glass card.
 */
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { colors, spacing, radii, typography } from '../../theme/tokens'
import { glassCard } from '../../theme/glassStyles'
import type { ChatMessage } from '../../stores/chatStore'
import ToolCallInline from './ToolCallInline'
import A2UISurfaceRenderer from './A2UISurfaceRenderer'

interface Props {
  message: ChatMessage
}

const styles: Record<string, React.CSSProperties> = {
  userRow: {
    display: 'flex',
    justifyContent: 'flex-end',
  },
  assistantRow: {
    display: 'flex',
    justifyContent: 'flex-start',
  },
  userBubble: {
    background: `linear-gradient(135deg, ${colors.primary}, ${colors.cyan})`,
    color: '#FFFFFF',
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderRadius: `${radii.lg}px ${radii.lg}px 4px ${radii.lg}px`,
    maxWidth: '75%',
    wordBreak: 'break-word' as const,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    lineHeight: 1.5,
  },
  assistantBubble: {
    ...glassCard(),
    padding: `${spacing.md}px ${spacing.lg}px`,
    borderRadius: `${radii.lg}px ${radii.lg}px ${radii.lg}px 4px`,
    maxWidth: '85%',
    wordBreak: 'break-word' as const,
    fontSize: typography.sizes.md,
    fontFamily: typography.fontFamily,
    lineHeight: 1.6,
    color: colors.textPrimary,
  },
  timestamp: {
    fontSize: typography.sizes.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  copyBtn: {
    background: 'none',
    border: 'none',
    color: colors.textMuted,
    cursor: 'pointer',
    fontSize: typography.sizes.xs,
    padding: `2px ${spacing.sm}px`,
    borderRadius: radii.sm,
    transition: 'color 0.15s ease',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  surfacesContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  toolCallsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: spacing.xs,
    marginTop: spacing.sm,
  },
  markdown: {
    fontFamily: typography.fontFamily,
  },
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

export default function MessageItem({ message }: Props) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={isUser ? styles.userRow : styles.assistantRow}>
      <div>
        <div style={isUser ? styles.userBubble : styles.assistantBubble}>
          {isUser ? (
            <span>{message.content}</span>
          ) : (
            <div className="chat-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {message.toolCalls && message.toolCalls.length > 0 && (
            <div style={styles.toolCallsContainer}>
              {message.toolCalls.map((tc, i) => (
                <ToolCallInline key={`${tc.toolName}-${i}`} toolCall={tc} />
              ))}
            </div>
          )}

          {message.surfaces && message.surfaces.length > 0 && (
            <div style={styles.surfacesContainer}>
              {message.surfaces.map((surface) => (
                <A2UISurfaceRenderer key={surface.id} surface={surface} />
              ))}
            </div>
          )}
        </div>

        <div style={styles.footer}>
          <span style={styles.timestamp}>
            {formatTime(message.timestamp)}
          </span>
          {!isUser && message.content && (
            <button
              style={styles.copyBtn}
              onClick={handleCopy}
              title="Copy message"
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
