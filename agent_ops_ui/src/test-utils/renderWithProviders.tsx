/* eslint-disable react-refresh/only-export-components */
/**
 * Test wrapper with all providers: QueryClientProvider, Zustand stores.
 * Resets stores between tests.
 */
import React from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { useDashboardStore } from '../stores/dashboardStore'
import { useSessionStore } from '../stores/sessionStore'
import { useProjectStore } from '../stores/projectStore'

/** Reset all Zustand stores to initial state. Call in beforeEach. */
export function resetStores(): void {
  useAuthStore.setState({
    user: null,
    accessToken: null,
    idToken: null,
    isGuest: false,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  })
  useChatStore.setState({
    messages: [],
    isStreaming: false,
    isProcessing: false,
    abortController: null,
    surfaces: new Map(),
    activeToolCalls: new Map(),
    suggestions: [],
    error: null,
  })
  useDashboardStore.setState({
    items: [],
    isOpen: false,
    activeTab: 'traces',
    isRailExpanded: false,
    metricsQueryLanguage: 0,
  })
  useSessionStore.setState({
    sessions: [],
    currentSessionId: null,
    isLoading: false,
  })
  useProjectStore.setState({
    projectId: 'test-project',
    recentProjects: [],
    starredProjects: [],
  })
}

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  })
}

interface WrapperProps {
  children: React.ReactNode
}

function AllProviders({ children }: WrapperProps) {
  const queryClient = React.useMemo(() => createTestQueryClient(), [])

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  return render(ui, { wrapper: AllProviders, ...options })
}

export { resetStores as resetAllStores }
