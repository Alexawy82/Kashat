import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// List all categories
export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/categories')
      if (error) throw new Error('Failed to fetch categories')
      return data as any[]
    },
  })
}

// Assign category to transaction
export function useAssignCategory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ txId, categoryId }: { txId: string; categoryId: string }) => {
      const { data, error } = await client.post('/api/transactions/{tx_id}/category', {
        params: { path: { tx_id: txId } },
        body: { category_id: categoryId }
      })
      if (error) throw new Error('Failed to assign category')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Get AI category suggestions for a transaction
export function useAICategorySuggestions(txId: string) {
  return useQuery({
    queryKey: ['ai-category-suggestions', txId],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/suggestions/smart-categories/{transaction_id}', {
        params: { path: { transaction_id: txId } }
      })
      if (error) throw new Error('Failed to fetch AI suggestions')
      return data as any
    },
    enabled: !!txId,
  })
}

// Apply AI category suggestion
export function useApplyAISuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      transaction_id: string
      category_name: string
      auto_create?: boolean
    }) => {
      const { data, error } = await client.post('/api/ai/suggestions/apply-smart-category', {
        body: params
      })
      if (error) throw new Error('Failed to apply suggestion')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Update transaction flags
export function useUpdateTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      txId: string
      is_business?: boolean
      is_income?: boolean
      is_adjustment?: boolean
    }) => {
      const { txId, ...body } = params
      const { data, error } = await client.patch('/api/transactions/{tx_id}', {
        params: { path: { tx_id: txId } },
        body
      })
      if (error) throw new Error('Failed to update transaction')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Delete transaction
export function useDeleteTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (txId: string) => {
      const { error } = await client.delete('/api/transactions/{tx_id}', {
        params: { path: { tx_id: txId } }
      })
      if (error) throw new Error('Failed to delete transaction')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// ==================== AI BULK ACTIONS ====================

// Detect duplicate transactions
export function useDuplicateDetection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.get('/api/ai/duplicates/detect')
      if (error) throw new Error('Failed to detect duplicates')
      return data as {
        duplicates_found: number
        groups: Array<{
          key: string
          transactions: Array<{ id: string; description: string; amount: number; date: string }>
        }>
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Merge duplicate transactions
export function useMergeDuplicates() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: { group_key?: string; auto_merge?: boolean }) => {
      const { data, error } = await client.post('/api/ai/duplicates/merge', {
        body: params
      })
      if (error) throw new Error('Failed to merge duplicates')
      return data as { merged_count: number }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Accept all AI category suggestions in batch (uses auto-categorize for uncategorized transactions)
export function useAcceptAllAISuggestions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { limit?: number }) => {
      // Use auto-categorize endpoint which applies AI categorization to uncategorized transactions
      const { data, error } = await client.post('/api/ai-categories/auto-categorize-uncategorized', {
        params: { query: { limit: params?.limit || 500 } }
      })
      if (error) throw new Error('Failed to accept AI suggestions')
      // Map response to expected format
      const result = data as {
        status: string
        results?: { categorized?: number; auto_applied?: number }
        message?: string
      }
      const acceptedCount = result.results?.categorized ?? result.results?.auto_applied ?? 0
      return {
        accepted_count: acceptedCount,
        skipped_count: 0,
        status: result.status,
        message: result.message
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Auto-categorize all uncategorized transactions
export function useAutoCategorizeUncategorized() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { limit?: number }) => {
      const { data, error } = await client.post('/api/ai-categories/auto-categorize-uncategorized', {
        params: { query: { limit: params?.limit } }
      })
      if (error) throw new Error('Failed to auto-categorize')
      const result = data as {
        status?: string
        results?: { auto_applied?: number }
        remaining?: number
        categorized_count?: number
        message?: string
      }
      return {
        status: result.status,
        message: result.message,
        categorized_count: result.categorized_count ?? result.results?.auto_applied ?? 0,
        remaining: result.remaining ?? 0
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Get category coverage stats
export function useCategoryCoverage() {
  return useQuery({
    queryKey: ['category-coverage'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai-categories/category-coverage')
      if (error) throw new Error('Failed to fetch category coverage')
      const result = data as {
        total_transactions?: number
        categorized_count?: number
        uncategorized_count?: number
        coverage_percent?: number
        success_rate?: number
      }
      const coveragePercent = result.coverage_percent ?? result.success_rate ?? 0
      return {
        total_transactions: result.total_transactions ?? 0,
        categorized_count: result.categorized_count ?? 0,
        uncategorized_count: result.uncategorized_count ?? 0,
        coverage_percent: coveragePercent
      }
    },
  })
}

// ==================== CATEGORY MANAGEMENT AI ====================

// Get category gap analysis
export function useCategoryGapAnalysis() {
  return useQuery({
    queryKey: ['category-gaps'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/categories/gap-analysis')
      if (error) throw new Error('Failed to fetch gap analysis')
      return data as {
        missing_categories: Array<{ name: string; suggested_parent?: string; frequency: number }>
        uncategorized_merchants: Array<{ merchant: string; count: number }>
      }
    },
  })
}

// Bootstrap standard categories
export function useBootstrapCategories() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/ai/categories/bootstrap')
      if (error) throw new Error('Failed to bootstrap categories')
      return data as { created_count: number; categories: string[] }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    }
  })
}

// Bulk fix all category gaps
export function useBulkFixCategories() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/ai/categories/bulk-fix')
      if (error) throw new Error('Failed to bulk fix categories')
      return data as { fixed_count: number }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Get AI category success metrics
export function useAISuccessMetrics() {
  return useQuery({
    queryKey: ['ai-success-metrics'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/categories/success-metrics')
      if (error) return null
      return data as {
        total_suggestions: number
        accepted: number
        rejected: number
        accuracy_rate: number
      }
    },
  })
}

// Get category usage stats
export function useCategoryUsageStats() {
  return useQuery({
    queryKey: ['category-usage'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/categories/usage-stats')
      if (error) return null
      return data as Array<{
        category_id: string
        category_name: string
        transaction_count: number
        total_amount: number
      }>
    },
  })
}

// ==================== IMPROVED CATEGORIZATION (Race-Condition Safe) ====================

export interface CategorizationJobResponse {
  status: 'started' | 'no_work' | 'already_running'
  job_id?: string
  total_transactions?: number
  batch_size?: number
  message: string
}

export interface CategorizationStatus {
  overall: {
    total_transactions: number
    categorized: number
    uncategorized: number
    percent_complete: number
  }
  current_job: {
    job_id: string
    total: number
    processed: number
    categorized: number
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'paused'
    progress_percent: number
    created_at: string
    completed_at: string | null
    error_message: string | null
  } | null
}

/**
 * Start a job to categorize ALL uncategorized transactions.
 *
 * Unlike the old auto-categorize endpoint, this:
 * 1. Pre-fetches all uncategorized IDs upfront (no race conditions)
 * 2. Creates a tracked job for progress monitoring
 * 3. Processes sequentially in background
 *
 * Use useCategorizationStatus() to monitor progress.
 */
export function useCategorizeAllTransactions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { batch_size?: number }) => {
      const { data, error } = await client.post('/api/ai-categories/categorize-all', {
        params: { query: { batch_size: params?.batch_size || 50 } }
      })
      if (error) throw new Error('Failed to start categorization job')
      return data as CategorizationJobResponse
    },
    onSuccess: () => {
      // Invalidate categorization status to trigger refresh
      queryClient.invalidateQueries({ queryKey: ['categorization-status'] })
    }
  })
}

/**
 * Get real-time categorization status.
 *
 * Returns overall stats (total, categorized, uncategorized, percent)
 * and current job progress if a job is running.
 *
 * @param pollInterval - How often to poll in ms (default: 3000, set to 0 to disable)
 */
export function useCategorizationStatus(pollInterval: number = 3000) {
  return useQuery({
    queryKey: ['categorization-status'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/categorization/status')
      if (error) throw new Error('Failed to fetch categorization status')
      return data as CategorizationStatus
    },
    refetchInterval: (query) => {
      // Only poll if there's an active job
      const data = query.state.data as CategorizationStatus | undefined
      if (data?.current_job?.status === 'processing') {
        return pollInterval
      }
      return false
    },
  })
}

/**
 * Hook that returns whether a categorization job is currently running.
 */
export function useIsCategorizationRunning() {
  const { data } = useCategorizationStatus()
  return data?.current_job?.status === 'processing'
}
