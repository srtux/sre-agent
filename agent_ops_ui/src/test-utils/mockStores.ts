/**
 * Pre-configured Zustand store states for testing.
 */
import { useAuthStore } from '../stores/authStore'
import { useChatStore, generateMessageId, type ChatMessage } from '../stores/chatStore'
import { useDashboardStore } from '../stores/dashboardStore'
import { useSessionStore, type Session } from '../stores/sessionStore'
import { useProjectStore } from '../stores/projectStore'

/** Set auth store to authenticated state. */
export function setAuthenticatedState(email = 'test@example.com'): void {
  useAuthStore.setState({
    user: { email, name: 'Test User', sub: 'user-123' },
    accessToken: 'test-access-token',
    idToken: 'test-id-token',
    isGuest: false,
    isAuthenticated: true,
    isLoading: false,
    error: null,
  })
}

/** Set auth store to guest state. */
export function setGuestState(): void {
  useAuthStore.setState({
    user: null,
    accessToken: 'dev-mode-bypass-token',
    idToken: null,
    isGuest: true,
    isAuthenticated: true,
    isLoading: false,
    error: null,
  })
}

/** Set chat store with sample messages. */
export function setChatWithMessages(): ChatMessage[] {
  const messages: ChatMessage[] = [
    {
      id: generateMessageId(),
      role: 'user',
      content: 'Investigate high latency on api-gateway',
      timestamp: new Date(Date.now() - 60_000).toISOString(),
    },
    {
      id: generateMessageId(),
      role: 'assistant',
      content: 'I\'ll investigate the high latency on your api-gateway service. Let me check traces, logs, and metrics.',
      timestamp: new Date(Date.now() - 55_000).toISOString(),
      suggestions: ['Show me the traces', 'Check error logs', 'View SLO status'],
    },
  ]
  useChatStore.setState({ messages })
  return messages
}

/** Set session store with sample sessions. */
export function setSessionsState(): Session[] {
  const sessions: Session[] = [
    { id: 'sess-1', title: 'Latency Investigation', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
    { id: 'sess-2', title: 'Error Rate Spike', createdAt: new Date(Date.now() - 86400_000).toISOString(), updatedAt: new Date(Date.now() - 86400_000).toISOString() },
    { id: 'sess-3', title: 'SLO Burn Analysis', createdAt: new Date(Date.now() - 172800_000).toISOString(), updatedAt: new Date(Date.now() - 172800_000).toISOString() },
  ]
  useSessionStore.setState({ sessions, currentSessionId: 'sess-1' })
  return sessions
}

/** Set project store with a project ID. */
export function setProjectState(projectId = 'my-gcp-project'): void {
  useProjectStore.setState({
    projectId,
    recentProjects: [projectId, 'other-project'],
    starredProjects: [projectId],
  })
}

/** Set dashboard store with sample items for a given type. */
export function setDashboardWithItems(count = 3): void {
  useDashboardStore.getState().clear()
  for (let i = 0; i < count; i++) {
    useDashboardStore.getState().addTrace(
      { traceId: `trace-${i}`, spans: [] },
      'get_traces',
      {},
    )
  }
}
