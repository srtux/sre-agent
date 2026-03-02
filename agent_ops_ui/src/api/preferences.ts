/**
 * Preferences API functions.
 */
import apiClient from './client'

interface ProjectPreference {
  project_id: string | null
}

export async function getProjectPreference(): Promise<string | null> {
  const { data } = await apiClient.get<ProjectPreference>(
    '/api/preferences/project',
  )
  return data.project_id
}

export async function setProjectPreference(projectId: string): Promise<void> {
  await apiClient.put('/api/preferences/project', { project_id: projectId })
}

export interface UserPreferences {
  theme?: string
  auto_open_dashboard?: boolean
  default_time_range?: string
  [key: string]: unknown
}

export async function getPreferences(): Promise<UserPreferences> {
  const { data } = await apiClient.get<UserPreferences>('/api/preferences')
  return data
}

export async function updatePreferences(
  prefs: Partial<UserPreferences>,
): Promise<void> {
  await apiClient.patch('/api/preferences', prefs)
}
