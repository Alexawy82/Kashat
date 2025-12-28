import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

export function useRecurringSummary() {
  return useQuery({
    queryKey: ['recurring', 'summary'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/summary')
      if (error) throw new Error('Failed to fetch recurring summary')
      return data as any
    },
    staleTime: 60_000,
  })
}

export function useRecurringByType(type: string) {
  return useQuery({
    queryKey: ['recurring', 'by-type', type],
    queryFn: async () => {
      const { data, error } = await client.get(`/api/recurring/${type}`)
      if (error) return []
      return (data as any) || []
    },
  })
}

export function useSubscriptions() {
  return useRecurringByType('subscriptions')
}

export function useBills() {
  return useRecurringByType('bills')
}

export function useLoans() {
  return useRecurringByType('loans')
}

export function useCreditCards() {
  return useRecurringByType('credit-cards')
}

export function useInsurance() {
  return useRecurringByType('insurance')
}

export function useConfirmWithLearning() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesIds: string[]) => {
      const results = await Promise.all(
        seriesIds.map((seriesId) =>
          client.post(`/api/recurring/confirm/${seriesId}/with-learning`)
        )
      )
      const errors = results.find((result) => result.error)
      if (errors?.error) throw errors.error
      return results.map((result) => result.data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-confirmed'] })
    },
  })
}

export function useRejectWithLearning() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ seriesIds, reason }: { seriesIds: string[]; reason?: string }) => {
      const results = await Promise.all(
        seriesIds.map((seriesId) =>
          client.post('/api/recurring/reject/{series_id}/with-learning', {
            params: { path: { series_id: seriesId }, query: { reason } },
          })
        )
      )
      const errors = results.find((result) => result.error)
      if (errors?.error) throw errors.error
      return results.map((result) => result.data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-confirmed'] })
    },
  })
}

export function useSubmitFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (feedback: {
      series_id: string
      original_type: string
      corrected_type?: string | null
      was_correct: boolean
      merchant_pattern?: string | null
      is_essential: boolean
      corrected_is_essential?: boolean | null
    }) => {
      const { data, error } = await client.post('/api/recurring/ai-workflow/feedback', {
        body: feedback,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-confirmed'] })
    },
  })
}

export function useRecurringInsights(limit = 6) {
  return useQuery({
    queryKey: ['recurring', 'insights', limit],
    queryFn: async () => {
      const { data, error } = await client.get(`/api/recurring/insights?limit=${limit}`)
      if (error) return []
      return (data as any) || []
    },
  })
}

export function useOptimizations(limit = 4) {
  return useQuery({
    queryKey: ['recurring', 'optimizations', limit],
    queryFn: async () => {
      const { data, error } = await client.get(`/api/recurring/insights/optimizations?limit=${limit}`)
      if (error) return []
      return (data as any) || []
    },
  })
}

export function useCancellationRisks(limit = 4) {
  return useQuery({
    queryKey: ['recurring', 'cancellation-risks', limit],
    queryFn: async () => {
      const { data, error } = await client.get(`/api/recurring/insights/cancellation-risks?limit=${limit}`)
      if (error) return []
      return (data as any) || []
    },
  })
}

export function useUpcomingPayments(days = 14) {
  return useQuery({
    queryKey: ['recurring', 'upcoming', days],
    queryFn: async () => {
      const { data, error } = await client.get(`/api/recurring/insights/upcoming?days=${days}`)
      if (error) return []
      return (data as any) || []
    },
  })
}

export function useSpendingByType() {
  return useQuery({
    queryKey: ['recurring', 'spending-by-type'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/insights/spending-by-type')
      if (error) return null
      return data as any
    },
  })
}

export function useAIWorkflowStats() {
  return useQuery({
    queryKey: ['recurring', 'ai-workflow', 'stats'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/ai-workflow/stats')
      if (error) return null
      return data as any
    },
  })
}

export function useAIAccuracy() {
  return useQuery({
    queryKey: ['recurring', 'ai-workflow', 'accuracy'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/ai-workflow/accuracy')
      if (error) return null
      return data as any
    },
  })
}

export function useReclassifyRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/recurring/reclassify')
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}

export function useMergeRecurringDuplicates() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/recurring/merge-duplicates')
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}

export function useReclassifyWithLLM() {
  const queryClient = useQueryClient()

  return useMutation<any, Error, number>({
    mutationFn: async (limit = 100) => {
      const { data, error } = await client.post(`/api/recurring/reclassify-with-llm?limit=${limit}`)
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}

export function useBackfillMemory() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/recurring/ai-workflow/backfill-memory')
      if (error) throw error
      return data as any
    },
  })
}

export function useIntelligenceCacheStats() {
  return useQuery({
    queryKey: ['recurring', 'intelligence-cache'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/intelligence/cache-stats')
      if (error) return null
      return data as any
    },
  })
}

export function useCleanupIntelligenceCache() {
  return useMutation<any, Error, number>({
    mutationFn: async (maxAgeDays = 60) => {
      const { data, error } = await client.post(`/api/recurring/intelligence/cleanup-cache?max_age_days=${maxAgeDays}`)
      if (error) throw error
      return data as any
    },
  })
}
