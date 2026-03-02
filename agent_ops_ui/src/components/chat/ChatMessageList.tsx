/**
 * Scrollable message list with auto-scroll on new messages.
 */
import { useRef, useEffect } from 'react'
import type { ChatMessage } from '../../stores/chatStore'
import MessageItem from './MessageItem'

interface Props {
  messages: ChatMessage[]
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    paddingBottom: 8,
  },
}

export default function ChatMessageList({ messages }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  const lastMessageContent = messages[messages.length - 1]?.content
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, lastMessageContent])

  return (
    <div style={styles.container}>
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}
      <div ref={endRef} />
    </div>
  )
}
