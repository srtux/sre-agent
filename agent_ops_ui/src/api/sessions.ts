/**
 * Session API functions.
 */
import apiClient from './client'
import type { Session } from '../stores/sessionStore'

interface SessionListResponse {
  sessions: Array<{
    id: string
    title?: string
    created_at?: string
    updated_at?: string
  }>
}

interface SessionCreateResponse {
  session_id: string
}

export async function listSessions(): Promise<Session[]> {
  const { data } = await apiClient.get<SessionListResponse>('/api/sessions')
  return data.sessions.map((s) => ({
    id: s.id,
    title: s.title || `Session ${s.id.slice(0, 8)}`,
    createdAt: s.created_at || new Date().toISOString(),
    updatedAt: s.updated_at || new Date().toISOString(),
  }))
}

export async function createSession(): Promise<string> {
  const { data } = await apiClient.post<SessionCreateResponse>('/api/sessions')
  return data.session_id
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/api/sessions/${sessionId}`)
}

export async function renameSession(
  sessionId: string,
  title: string,
): Promise<void> {
  await apiClient.patch(`/api/sessions/${sessionId}`, { title })
}
