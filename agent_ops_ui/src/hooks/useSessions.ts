/**
 * React Query hooks for session CRUD.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listSessions,
  createSession,
  deleteSession,
  renameSession,
} from '../api/sessions'
import { useSessionStore } from '../stores/sessionStore'

const SESSIONS_KEY = ['sessions'] as const

export function useSessions() {
  const setSessions = useSessionStore((s) => s.setSessions)

  return useQuery({
    queryKey: SESSIONS_KEY,
    queryFn: async () => {
      const sessions = await listSessions()
      setSessions(sessions)
      return sessions
    },
    staleTime: 30_000,
  })
}

export function useCreateSession() {
  const queryClient = useQueryClient()
  const addSession = useSessionStore((s) => s.addSession)
  const setCurrentSession = useSessionStore((s) => s.setCurrentSession)

  return useMutation({
    mutationFn: createSession,
    onSuccess: (sessionId) => {
      const newSession = {
        id: sessionId,
        title: `Session ${sessionId.slice(0, 8)}`,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      addSession(newSession)
      setCurrentSession(sessionId)
      queryClient.invalidateQueries({ queryKey: SESSIONS_KEY })
    },
  })
}

export function useDeleteSession() {
  const queryClient = useQueryClient()
  const removeSession = useSessionStore((s) => s.removeSession)

  return useMutation({
    mutationFn: deleteSession,
    onSuccess: (_data, sessionId) => {
      removeSession(sessionId)
      queryClient.invalidateQueries({ queryKey: SESSIONS_KEY })
    },
  })
}

export function useRenameSession() {
  const queryClient = useQueryClient()
  const updateSessionTitle = useSessionStore((s) => s.updateSessionTitle)

  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      renameSession(sessionId, title),
    onSuccess: (_data, { sessionId, title }) => {
      updateSessionTitle(sessionId, title)
      queryClient.invalidateQueries({ queryKey: SESSIONS_KEY })
    },
  })
}
