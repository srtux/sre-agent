/**
 * Saved queries CRUD — persisted via backend or localStorage fallback.
 */
import apiClient from './client'

export interface SavedQuery {
  id: string
  query: string
  language: string
  name: string
  createdAt?: string
}

const STORAGE_KEY = 'sre_saved_queries'

function localLoad(): SavedQuery[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function localSave(queries: SavedQuery[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queries))
}

/** Fetch all saved queries. */
export async function getSavedQueries(): Promise<SavedQuery[]> {
  try {
    const { data } = await apiClient.get<SavedQuery[]>('/api/saved-queries')
    return data
  } catch {
    return localLoad()
  }
}

/** Save a new query. */
export async function saveQuery(
  query: string,
  language: string,
  name: string,
): Promise<void> {
  try {
    await apiClient.post('/api/saved-queries', { query, language, name })
  } catch {
    const queries = localLoad()
    queries.unshift({
      id: `sq-${Date.now()}`,
      query,
      language,
      name,
      createdAt: new Date().toISOString(),
    })
    localSave(queries.slice(0, 50))
  }
}

/** Delete a saved query by ID. */
export async function deleteSavedQuery(id: string): Promise<void> {
  try {
    await apiClient.delete(`/api/saved-queries/${id}`)
  } catch {
    const queries = localLoad().filter((q) => q.id !== id)
    localSave(queries)
  }
}
