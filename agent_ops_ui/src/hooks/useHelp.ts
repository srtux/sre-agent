import { useQuery } from '@tanstack/react-query'
import apiClient from '../api/client'

export interface HelpItem {
  id: string
  title: string
  description: string
  content: string
  category: string
}

const HELP_KEY = 'help' as const

async function fetchHelp(category?: string): Promise<HelpItem[]> {
  const res = await apiClient.get<{ items: HelpItem[] }>('/api/help', {
    params: category ? { category } : undefined,
  })
  return res.data.items
}

export function useHelp(category?: string) {
  return useQuery({
    queryKey: [HELP_KEY, category],
    queryFn: () => fetchHelp(category),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })
}
