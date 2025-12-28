import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// ==================== RULES ====================

export function useRules() {
  return useQuery({
    queryKey: ['rules'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/rules')
      if (error) throw new Error('Failed to fetch rules')
      return (data as any) || []
    }
  })
}

export function useRuleSuggestions() {
  return useQuery({
    queryKey: ['rule-suggestions'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/rules/suggestions')
      if (error) return []
      return (data as any) || []
    }
  })
}

export function useCreateRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (rule: {
      priority: number
      predicate: Record<string, any>
      action: Record<string, any>
      enabled?: boolean
    }) => {
      const { data, error } = await client.post('/api/rules', {
        body: rule
      })
      if (error) throw new Error('Failed to create rule')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      queryClient.invalidateQueries({ queryKey: ['rule-suggestions'] })
    }
  })
}

export function useDeleteRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (ruleId: string) => {
      const { error } = await client.delete('/api/rules/{rule_id}', {
        params: { path: { rule_id: ruleId } }
      })
      if (error) throw new Error('Failed to delete rule')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    }
  })
}

export function useApplyRule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (ruleId: string) => {
      const { data, error } = await client.post('/api/rules/{rule_id}/apply', {
        params: { path: { rule_id: ruleId } }
      })
      if (error) throw new Error('Failed to apply rule')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

export function useApplyAllRules() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/rules/apply-all')
      if (error) throw new Error('Failed to apply rules')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['transaction-stats'] })
    }
  })
}

export function usePreviewRule() {
  return useMutation({
    mutationFn: async (predicate: Record<string, any>) => {
      const { data, error } = await client.post('/api/rules/preview', {
        body: { predicate, limit: 20 }
      })
      if (error) throw new Error('Failed to preview rule')
      return data as any[]
    }
  })
}

// ==================== RECURRING ====================

export function useRecurringSuggestions() {
  return useQuery({
    queryKey: ['recurring-suggestions'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/pending')
      if (error) return []
      return (data as any) || []
    }
  })
}

export function useConfirmedRecurring() {
  return useQuery({
    queryKey: ['recurring-confirmed'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/recurring/confirmed')
      if (error) return []
      return (data as any) || []
    }
  })
}

export function useConfirmRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesIds: string[]) => {
      const { data, error } = await client.post('/api/recurring/confirm', {
        body: { series_ids: seriesIds }
      })
      if (error) throw new Error('Failed to confirm recurring series')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-confirmed'] })
    }
  })
}

export function useRejectRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (seriesIds: string[]) => {
      const { data, error } = await client.post('/api/recurring/reject', {
        body: { series_ids: seriesIds }
      })
      if (error) throw new Error('Failed to reject recurring series')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-suggestions'] })
    }
  })
}

export function useRunRecurringDetection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: {
      min_occurrences?: number
      tol?: number
      limit?: number
      include_short_cadence?: boolean
    }) => {
      const { data, error } = await client.post('/api/recurring/suggest', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to run recurring detection')
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-confirmed'] })
    }
  })
}

// Fetch sparkline data for a recurring series
export function useRecurringSparkline(seriesId: string | null) {
  return useQuery({
    queryKey: ['recurring-sparkline', seriesId],
    queryFn: async () => {
      if (!seriesId) return []
      const { data, error } = await client.get('/api/recurring/{series_id}/transactions', {
        params: { path: { series_id: seriesId }, query: { limit: 12 } }
      })
      if (error) return []
      return (data as { date: string; amount: number }[]) || []
    },
    enabled: !!seriesId
  })
}

// ==================== TRANSFERS ====================

export function useTransferSuggestions(limit: number = 10) {
  return useQuery({
    queryKey: ['transfer-suggestions', limit],
    queryFn: async () => {
      const { data, error } = await client.get('/api/transfers', {
        params: { query: { status: 'pending' } }
      })
      if (error) return { suggestions: [] }
      const rows = (data as any[]) || []
      const suggestions = rows.map((row) => ({
        group_id: row.group_id,
        left_id: row.left_tx_id,
        right_id: row.right_tx_id,
        confidence: row.score,
        method: row.method,
        left: {
          id: row.left_tx_id,
          posted_at: row.left_date,
          amount: row.left_amount,
          description_norm: row.left_desc,
          account_id: row.left_account_id,
        },
        right: {
          id: row.right_tx_id,
          posted_at: row.right_date,
          amount: row.right_amount,
          description_norm: row.right_desc,
          account_id: row.right_account_id,
        },
      }))
      return { suggestions } as any
    }
  })
}

export function useConfirmedTransfers() {
  return useQuery({
    queryKey: ['transfers-confirmed'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/transfers', {
        params: { query: { status: 'confirmed' } }
      })
      if (error) return []
      return (data as any) || []
    }
  })
}

export function useRunTransferDetection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: {
      max_days?: number
      amount_tolerance_pct?: number
      min_score?: number
      limit?: number
    }) => {
      // Use v3 hybrid detection (recommended) instead of v2
      const { data, error } = await client.post('/api/transfers/suggest', {
        params: {
          query: {
            max_days: params?.max_days ?? 3,
            amount_tolerance_pct: params?.amount_tolerance_pct ?? 0.02,
            min_score: params?.min_score ?? 0.5,
            limit: params?.limit ?? 5000,
          }
        }
      })
      if (error) throw new Error('Failed to run transfer detection')
      return data as {
        created: number
        skipped_existing: number
        skipped_low_score: number
        candidates_scanned: number
        candidates: any[]
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['transfers-confirmed'] })
    }
  })
}

export function useConfirmTransfer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: { left_id: string; right_id: string }) => {
      const { data, error } = await client.post('/api/transfers/confirm', {
        body: { left_tx_id: params.left_id, right_tx_id: params.right_id }
      })
      if (error) throw new Error('Failed to confirm transfer')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['transfers-confirmed'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

export function useRejectTransfer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: { left_id: string; right_id: string }) => {
      const { data, error } = await client.post('/api/transfers/reject', {
        body: { left_tx_id: params.left_id, right_tx_id: params.right_id }
      })
      if (error) throw new Error('Failed to reject transfer')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-suggestions'] })
    }
  })
}

export function useBulkConfirmTransfers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (groupIds: string[]) => {
      const { data, error } = await client.post('/api/transfers/confirm', {
        body: { group_ids: groupIds }
      })
      if (error) throw new Error('Failed to bulk confirm transfers')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['transfers-confirmed'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

export function useBulkRejectTransfers() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (groupIds: string[]) => {
      const { data, error } = await client.post('/api/transfers/reject', {
        body: { group_ids: groupIds }
      })
      if (error) throw new Error('Failed to bulk reject transfers')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-suggestions'] })
    }
  })
}

// ==================== P2P (VENMO/CASHAPP/WU) ====================

export type P2PSummaryRow = {
  provider: string
  counterparty: string
  count: number
  total_out: number
  total_in: number
  net: number
  first_date: string
  last_date: string
}

export function useP2PSummary(params?: { provider?: string; limit?: number }) {
  const provider = params?.provider
  const limit = params?.limit ?? 50
  return useQuery({
    queryKey: ['p2p-summary', provider, limit],
    queryFn: async () => {
      const { data, error } = await client.get('/api/p2p/summary', {
        params: { query: { provider, limit } }
      })
      if (error) return []
      return (data as any as P2PSummaryRow[]) || []
    }
  })
}

export function useRunP2PDetection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/detect/p2p', {
        params: { query: { commit: true } }
      })
      if (error) throw new Error('Failed to run P2P detection')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

export type P2PTxRow = {
  id: string
  posted_at: string
  amount: number
  currency: string | null
  description_norm: string
  p2p_direction: string | null
  p2p_counterparty: string | null
  account_id: string
  category_name: string | null
}

export function useP2PTransactions(params?: { provider?: string; counterparty?: string; limit?: number }) {
  const provider = params?.provider
  const counterparty = params?.counterparty
  const limit = params?.limit ?? 50
  return useQuery({
    queryKey: ['p2p-transactions', provider, counterparty, limit],
    queryFn: async () => {
      if (!provider) return []
      const { data, error } = await client.get('/api/p2p/transactions', {
        params: { query: { provider, counterparty, limit } }
      })
      if (error) return []
      return (data as any as P2PTxRow[]) || []
    },
    enabled: !!provider
  })
}

export function usePatchTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (args: { txId: string; patch: Record<string, any> }) => {
      const { data, error } = await client.patch('/api/transactions/{tx_id}', {
        params: { path: { tx_id: args.txId } },
        body: args.patch
      })
      if (error) throw new Error('Failed to patch transaction')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// ==================== DETECTION ====================

// Run all detectors at once (P2P, Income, Adjustments, Zelle)
export function useRunAllDetectors() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/detect/auto')
      if (error) throw new Error('Failed to run all detectors')
      return data as {
        p2p: { detected: number }
        income: { detected: number }
        adjustments: { detected: number }
        zelle: { detected: number }
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-suggestions'] })
    }
  })
}

// Detect Zelle transactions
export function useDetectZelle() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { commit?: boolean }) => {
      const { data, error } = await client.post('/api/detect/zelle', {
        params: { query: { commit: params?.commit ?? true } }
      })
      if (error) throw new Error('Failed to detect Zelle transactions')
      return data as { detected: number; committed: boolean }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
    }
  })
}

// Detect income transactions
export function useDetectIncome() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { commit?: boolean }) => {
      const { data, error } = await client.post('/api/detect/income', {
        params: { query: { commit: params?.commit ?? true } }
      })
      if (error) throw new Error('Failed to detect income')
      return data as { detected: number; committed: boolean }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Detect adjustment transactions
export function useDetectAdjustments() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { commit?: boolean }) => {
      const { data, error } = await client.post('/api/detect/adjustments', {
        params: { query: { commit: params?.commit ?? true } }
      })
      if (error) throw new Error('Failed to detect adjustments')
      return data as { detected: number; committed: boolean }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// ==================== AI-ENHANCED TRANSFER DETECTION ====================

export type AITransferJobResult = {
  job_id: string
  status: string
  total_pairs: number
  message?: string
  transfers_found?: number
  high_confidence?: number
  medium_confidence?: number
}

export type AITransferJobStatus = {
  job_id: string
  job_type: string
  total_pairs: number
  processed_pairs: number
  transfers_found: number
  status: string
  created_at: string
  completed_at: string | null
  error_message: string | null
  progress_percent: number
}

export type AITransferStats = {
  total_matches: number
  pending: number
  confirmed: number
  by_method: Record<string, number>
  by_confidence: {
    high: number
    medium: number
    low: number
  }
  latest_job: {
    job_id: string | null
    status: string | null
    total: number
    processed: number
    found: number
  } | null
}

export type AITransferAnalysis = {
  left_id: string
  right_id: string
  is_transfer: boolean
  confidence: number
  reasoning: string
  method: string
  heuristic_score: number
  scores: {
    date_proximity: number
    amount_match: number
    description_similarity: number
  }
  provider: string | null
  latency_ms: number | null
}

// Start AI-enhanced transfer detection job
export function useRunAITransferDetection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { limit?: number; use_ai?: boolean }) => {
      const { data, error } = await client.post('/api/transfers/ai/detect', {
        params: {
          query: {
            limit: params?.limit ?? 5000,
            use_ai: params?.use_ai ?? true
          }
        }
      })
      if (error) throw new Error('Failed to start AI transfer detection')
      return data as AITransferJobResult
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-suggestions'] })
      queryClient.invalidateQueries({ queryKey: ['transfers-confirmed'] })
      queryClient.invalidateQueries({ queryKey: ['ai-transfer-stats'] })
    }
  })
}

// Get AI transfer detection job status
export function useAITransferJob(jobId: string | null) {
  return useQuery({
    queryKey: ['ai-transfer-job', jobId],
    queryFn: async () => {
      if (!jobId) return null
      const { data, error } = await client.get('/api/transfers/ai/job/{job_id}', {
        params: { path: { job_id: jobId } }
      })
      if (error) return null
      return data as AITransferJobStatus
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      // Poll every 2 seconds while job is running
      if (query.state.data && query.state.data.status === 'processing') return 2000
      return false
    }
  })
}

// Cancel AI transfer detection job
export function useCancelAITransferJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobId: string) => {
      const { data, error } = await client.post('/api/transfers/ai/job/{job_id}/cancel', {
        params: { path: { job_id: jobId } }
      })
      if (error) throw new Error('Failed to cancel job')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-transfer-job'] })
    }
  })
}

// Get AI transfer detection stats
export function useAITransferStats() {
  return useQuery({
    queryKey: ['ai-transfer-stats'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/transfers/ai/stats')
      if (error) return null
      return data as AITransferStats
    }
  })
}

// Analyze a specific transaction pair with AI
export function useAnalyzeTransferPair() {
  return useMutation({
    mutationFn: async (params: { left_id: string; right_id: string }) => {
      const { data, error } = await client.post('/api/transfers/ai/analyze-pair', {
        params: {
          query: {
            left_id: params.left_id,
            right_id: params.right_id
          }
        }
      })
      if (error) throw new Error('Failed to analyze transfer pair')
      return data as AITransferAnalysis
    }
  })
}

// Submit feedback on transfer detection
export function useSubmitTransferFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      left_id: string
      right_id: string
      was_correct: boolean
      user_action: 'confirmed' | 'rejected'
    }) => {
      const { data, error } = await client.post('/api/transfers/ai/feedback', {
        params: {
          query: {
            left_id: params.left_id,
            right_id: params.right_id,
            was_correct: params.was_correct,
            user_action: params.user_action
          }
        }
      })
      if (error) throw new Error('Failed to submit feedback')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-transfer-stats'] })
    }
  })
}
