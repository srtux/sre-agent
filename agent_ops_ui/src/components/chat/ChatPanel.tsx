/**
 * Main chat container — messages list + input area + typing indicator.
 * Ported from autosre/lib/widgets/conversation/chat_panel_wrapper.dart
 */
import { colors } from '../../theme/tokens'
import { useChatStore } from '../../stores/chatStore'
import ChatMessageList from './ChatMessageList'
import ChatInputArea from './ChatInputArea'
import HeroEmptyState from './HeroEmptyState'
import SuggestionChips from './SuggestionChips'
import TypingIndicator from './TypingIndicator'
import { useAgentStream } from '../../hooks/useAgentStream'
import { useSessionStore } from '../../stores/sessionStore'

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: colors.background,
  },
  messageArea: {
    flex: 1,
    overflow: 'auto',
    padding: '16px',
  },
}

export default function ChatPanel() {
  const messages = useChatStore((s) => s.messages)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const suggestions = useChatStore((s) => s.suggestions)
  const error = useChatStore((s) => s.error)
  const sessionId = useSessionStore((s) => s.currentSessionId)
  const { sendMessage, cancel } = useAgentStream()

  const handleSend = (text: string) => {
    sendMessage({ message: text, sessionId: sessionId ?? undefined })
  }

  const isEmpty = messages.length === 0

  return (
    <div style={styles.container}>
      <div style={styles.messageArea}>
        {isEmpty ? (
          <HeroEmptyState onSuggestionClick={handleSend} />
        ) : (
          <>
            <ChatMessageList messages={messages} />
            {isStreaming && <TypingIndicator />}
          </>
        )}
      </div>

      {error && (
        <div
          style={{
            padding: '8px 16px',
            background: 'rgba(255, 82, 82, 0.08)',
            color: colors.error,
            fontSize: '13px',
            borderTop: `1px solid rgba(255, 82, 82, 0.2)`,
          }}
        >
          {error}
        </div>
      )}

      {suggestions.length > 0 && !isStreaming && (
        <SuggestionChips
          suggestions={suggestions}
          onSelect={handleSend}
        />
      )}

      <ChatInputArea
        onSend={handleSend}
        onCancel={cancel}
        isStreaming={isStreaming}
      />
    </div>
  )
}
