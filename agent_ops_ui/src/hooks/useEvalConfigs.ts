import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import type { EvalConfig, EvalConfigsResponse } from '../types'

const EVAL_CONFIGS_KEY = ['eval-configs'] as const

async function fetchEvalConfigs(): Promise<EvalConfig[]> {
  const res = await axios.get<EvalConfigsResponse>('/api/v1/evals/config')
  return res.data.configs
}

export function useEvalConfigs() {
  return useQuery({
    queryKey: EVAL_CONFIGS_KEY,
    queryFn: fetchEvalConfigs,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}

interface UpsertEvalConfigParams {
  agentName: string
  isEnabled: boolean
  samplingRate: number
  metrics: string[]
}

export function useUpsertEvalConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: UpsertEvalConfigParams) => {
      const res = await axios.post(`/api/v1/evals/config/${encodeURIComponent(params.agentName)}`, {
        is_enabled: params.isEnabled,
        sampling_rate: params.samplingRate,
        metrics: params.metrics,
      })
      return res.data.config as EvalConfig
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EVAL_CONFIGS_KEY })
    },
  })
}

export function useDeleteEvalConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (agentName: string) => {
      await axios.delete(`/api/v1/evals/config/${encodeURIComponent(agentName)}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EVAL_CONFIGS_KEY })
    },
  })
}
