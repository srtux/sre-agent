/**
 * Session state store (Zustand).
 * Ported from autosre/lib/services/session_service.dart
 */
import { create } from 'zustand'

export interface Session {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

interface SessionState {
  sessions: Session[]
  currentSessionId: string | null
  isLoading: boolean

  setSessions: (sessions: Session[]) => void
  setCurrentSession: (id: string | null) => void
  addSession: (session: Session) => void
  removeSession: (id: string) => void
  updateSessionTitle: (id: string, title: string) => void
  setLoading: (loading: boolean) => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  currentSessionId: null,
  isLoading: false,

  setSessions: (sessions) => set({ sessions }),

  setCurrentSession: (id) => set({ currentSessionId: id }),

  addSession: (session) =>
    set((state) => ({ sessions: [session, ...state.sessions] })),

  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      currentSessionId:
        state.currentSessionId === id ? null : state.currentSessionId,
    })),

  updateSessionTitle: (id, title) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id ? { ...s, title } : s,
      ),
    })),

  setLoading: (loading) => set({ isLoading: loading }),
}))
