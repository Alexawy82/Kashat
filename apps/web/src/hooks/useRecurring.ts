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

/**
 * @deprecated Use `useAllRecurring()` instead which fetches all types in one request.
 * This hook makes a separate API call for each type.
 */
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

/**
 * @deprecated Use `useAllRecurring()` and access `data.by_type.subscription` instead.
 */
export function useSubscriptions() {
  return useRecurringByType('subscriptions')
}

/**
 * @deprecated Use `useAllRecurring()` and access `data.by_type.bill` instead.
 */
export function useBills() {
  return useRecurringByType('bills')
}

/**
 * @deprecated Use `useAllRecurring()` and access `data.by_type.loan` instead.
 */
export function useLoans() {
  return useRecurringByType('loans')
}

/**
 * @deprecated Use `useAllRecurring()` and access `data.by_type.credit_card` instead.
 */
export function useCreditCards() {
  return useRecurringByType('credit-cards')
}

/**
 * @deprecated Use `useAllRecurring()` and access `data.by_type.insurance` instead.
 */
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

// ============ Series Action Hooks ============

export function useMarkPaid() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesId: string) => {
      const { data, error } = await client.post(`/api/recurring/${seriesId}/mark-paid`)
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useSkipNext() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesId: string) => {
      const { data, error } = await client.post(`/api/recurring/${seriesId}/skip-next`)
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function usePauseSeries() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesId: string) => {
      const { data, error } = await client.post(`/api/recurring/${seriesId}/pause`)
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useResumeSeries() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesId: string) => {
      const { data, error } = await client.post(`/api/recurring/${seriesId}/resume`)
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

export function useCancelSeries() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesId: string) => {
      const { data, error } = await client.post(`/api/recurring/${seriesId}/cancel`)
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
    },
  })
}

// =============================================================================
// Consolidated Hooks - Reduce API calls
// =============================================================================

export interface RecurringSeries {
  id: string
  series_id?: string
  name: string
  display_name?: string
  amount_mean: number
  monthly_equivalent?: number
  cadence: string
  recurring_type: string
  recurring_type_label?: string
  sub_category?: string
  sub_category_label?: string
  is_essential: boolean
  status: string
  next_date?: string
  last_date?: string
  occurrences?: number
  account_name?: string
  annual_cost?: number
}

export interface AllEnrichedResponse {
  all: RecurringSeries[]
  by_type: {
    subscription: RecurringSeries[]
    bill: RecurringSeries[]
    loan: RecurringSeries[]
    credit_card: RecurringSeries[]
    insurance: RecurringSeries[]
    unknown: RecurringSeries[]
  }
  summary: {
    total_count: number
    total_monthly: number
    essential_monthly: number
    discretionary_monthly: number
    by_type: Record<string, { count: number; monthly: number }>
  }
  pending_count: number
}

/**
 * Consolidated hook that fetches all recurring data in one API call.
 * Replaces: useSubscriptions, useBills, useLoans, useCreditCards, useInsurance
 */
export function useAllRecurring() {
  return useQuery({
    queryKey: ['recurring', 'all-enriched'],
    queryFn: async () => {
      const { data, error } = await client.get<AllEnrichedResponse>('/api/recurring/all-enriched')
      if (error) throw error
      return data as AllEnrichedResponse
    },
    staleTime: 60_000, // 1 minute
  })
}

/**
 * Trigger reclassification of all series with updated patterns
 */
export function useReclassifyAll() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/recurring/reclassify-all')
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}

/**
 * Reject false positives (gas stations, fast food, etc.)
 */
export function useRejectFalsePositives() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/recurring/reject-false-positives')
      if (error) throw error
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}
