import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '../api/client'

export interface ToolConfig {
  name: string
  description: string
  enabled: boolean
  category: string
}

const TOOL_CONFIGS_KEY = ['tool-configs'] as const

async function fetchToolConfigs(): Promise<ToolConfig[]> {
  const res = await apiClient.get<{ tools: ToolConfig[] }>('/api/tools/config')
  return res.data.tools
}

export function useToolConfigs() {
  return useQuery({
    queryKey: TOOL_CONFIGS_KEY,
    queryFn: fetchToolConfigs,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}

export function useUpdateToolConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (update: { name: string; enabled: boolean }) => {
      const res = await apiClient.patch('/api/tools/config', update)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TOOL_CONFIGS_KEY })
    },
  })
}
