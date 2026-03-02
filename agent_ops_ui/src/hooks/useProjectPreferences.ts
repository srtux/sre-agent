/**
 * React Query hook for project preferences.
 */
import { useQuery } from '@tanstack/react-query'
import { getProjectPreference } from '../api/preferences'
import { useProjectStore } from '../stores/projectStore'

export function useProjectPreferences() {
  const setProjectId = useProjectStore((s) => s.setProjectId)
  const currentProjectId = useProjectStore((s) => s.projectId)

  return useQuery({
    queryKey: ['projectPreference'],
    queryFn: async () => {
      const projectId = await getProjectPreference()
      // Only update the store if no project is currently set
      if (projectId && !currentProjectId) {
        setProjectId(projectId)
      }
      return projectId
    },
    staleTime: 60_000,
  })
}
