import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '../api/client'

export interface CustomDashboard {
  id: string
  name: string
  description: string
  widgetCount: number
  lastModified: string
}

const DASHBOARDS_KEY = ['custom-dashboards'] as const

async function fetchDashboards(): Promise<CustomDashboard[]> {
  const res = await apiClient.get<{ dashboards: CustomDashboard[] }>('/api/dashboards')
  return res.data.dashboards
}

export function useCustomDashboards() {
  return useQuery({
    queryKey: DASHBOARDS_KEY,
    queryFn: fetchDashboards,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}

export function useCreateDashboard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: { name: string; description: string }) => {
      const res = await apiClient.post('/api/dashboards', params)
      return res.data as CustomDashboard
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARDS_KEY })
    },
  })
}

export function useDeleteDashboard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/dashboards/${encodeURIComponent(id)}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARDS_KEY })
    },
  })
}
