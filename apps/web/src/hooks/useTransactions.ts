import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { Transaction, TransactionFilter, PaginatedResponse, TransactionStats } from '@/types/domain'

// Mutation types
interface UpdateTransactionParams {
  txId: string
  is_business?: boolean
  is_income?: boolean
  is_adjustment?: boolean
  ai_merchant_name?: string | null
}

interface SetCategoryParams {
  txId: string
  categoryId: string
  categoryName?: string
}

export function useTransactions(filter: TransactionFilter) {
  return useQuery({
    queryKey: ['transactions', filter],
    queryFn: async (): Promise<PaginatedResponse<Transaction>> => {
      const { data, error } = await client.get('/api/transactions', {
        params: {
          query: {
            limit: filter.limit,
            offset: (filter.page - 1) * filter.limit,
            desc: filter.search || undefined,
            sort_by: filter.sortBy,
            sort_dir: filter.sortDir,
            uncategorized: filter.uncategorized || undefined,
            has_ai_suggestions: filter.hasAiSuggestions,
            is_business: filter.isBusiness,
            is_income: filter.isIncome,
            category_id: filter.categoryId || undefined,
            account_id: filter.accountId || undefined,
            start_date: filter.startDate || undefined,
            end_date: filter.endDate || undefined,
          }
        }
      })

      if (error) {
        throw new Error('Failed to fetch transactions')
      }

      const items = Array.isArray(data) ? data : (data as any)?.items || []
      const total = (data as any)?.total || items.length

      return {
        items: items.map((item: any) => ({
          id: item.id,
          date: item.date || item.posted_at,
          amount: item.amount,
          description: item.description_norm || item.description,
          merchant: item.ai_merchant_name || item.description_norm || item.description,
          category: item.category_name || item.category?.name || 'Uncategorized',
          category_id: item.category_id,
          account_id: item.account_id,
          is_business: item.is_business,
          is_income: item.is_income,
          is_adjustment: item.is_adjustment,
          ai_confidence: item.ai_confidence_score,
          ai_suggestions: item.ai_category_suggestions,
          is_recurring: Boolean(item.is_recurring || item.recurring_series_id),
          status: 'posted',
          // Confidence: high (>0.8), medium (>0.5), low (<=0.5), or null if not scored
          confidence: item.ai_confidence_score == null ? null :
                      item.ai_confidence_score > 0.8 ? 'high' :
                      item.ai_confidence_score > 0.5 ? 'medium' : 'low'
        })),
        total,
        page: filter.page,
        limit: filter.limit,
        total_pages: Math.ceil(total / filter.limit)
      }
    },
    placeholderData: keepPreviousData, // Use TanStack Query's built-in previous data preservation
    staleTime: 30000, // Keep data fresh for 30 seconds to prevent flicker
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
  })
}

// Transaction stats for filter counts
export function useTransactionStats(filter: Omit<TransactionFilter, 'page' | 'limit' | 'sortBy' | 'sortDir'> = {}) {
  return useQuery({
    queryKey: ['transaction-stats', filter],
    queryFn: async (): Promise<TransactionStats> => {
      const { data, error } = await client.get('/api/transactions/stats', {
        params: {
          query: {
            desc: filter.search || undefined,
            uncategorized: filter.uncategorized || undefined,
            has_ai_suggestions: filter.hasAiSuggestions,
            is_business: filter.isBusiness,
            is_income: filter.isIncome,
            category_id: filter.categoryId || undefined,
          }
        }
      })

      if (error) {
        throw new Error('Failed to fetch transaction stats')
      }

      return {
        total: (data as any)?.total || 0,
        minDate: (data as any)?.min_date,
        maxDate: (data as any)?.max_date,
      }
    },
  })
}

// Delete a transaction with optimistic update
export function useDeleteTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (txId: string) => {
      const { error } = await client.delete('/api/transactions/{tx_id}', {
        params: { path: { tx_id: txId } }
      })
      if (error) throw new Error('Failed to delete transaction')
      return { deleted: txId }
    },
    // Optimistic delete - immediately remove from UI
    onMutate: async (txId) => {
      await queryClient.cancelQueries({ queryKey: ['transactions'] })
      const previousData = queryClient.getQueriesData({ queryKey: ['transactions'] })

      queryClient.setQueriesData({ queryKey: ['transactions'] }, (old: any) => {
        if (!old?.items) return old
        return {
          ...old,
          items: old.items.filter((item: any) => item.id !== txId),
          total: Math.max(0, (old.total || 0) - 1)
        }
      })

      return { previousData }
    },
    onError: (_err, _variables, context) => {
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['transaction-stats'] })
    }
  })
}

// Update transaction fields with optimistic update
export function useUpdateTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ txId, ...updates }: UpdateTransactionParams) => {
      const { data, error } = await client.patch('/api/transactions/{tx_id}', {
        params: { path: { tx_id: txId } },
        body: updates
      })
      if (error) throw new Error('Failed to update transaction')
      return data
    },
    // Optimistic update
    onMutate: async ({ txId, ...updates }) => {
      await queryClient.cancelQueries({ queryKey: ['transactions'] })
      const previousData = queryClient.getQueriesData({ queryKey: ['transactions'] })

      queryClient.setQueriesData({ queryKey: ['transactions'] }, (old: any) => {
        if (!old?.items) return old
        return {
          ...old,
          items: old.items.map((item: any) =>
            item.id === txId ? { ...item, ...updates } : item
          )
        }
      })

      return { previousData }
    },
    onError: (_err, _variables, context) => {
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['transaction-stats'] })
    }
  })
}

// Set transaction category with optimistic update
export function useSetTransactionCategory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ txId, categoryId }: SetCategoryParams) => {
      const { data, error } = await client.post('/api/transactions/{tx_id}/category', {
        params: { path: { tx_id: txId } },
        body: { category_id: categoryId }
      })
      if (error) throw new Error('Failed to set category')
      return data
    },
    // Optimistic update for instant UI feedback
    onMutate: async ({ txId, categoryId, categoryName }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['transactions'] })

      // Snapshot current data for all transaction queries
      const previousData = queryClient.getQueriesData({ queryKey: ['transactions'] })

      // Optimistically update the transaction in all cached queries
      queryClient.setQueriesData({ queryKey: ['transactions'] }, (old: any) => {
        if (!old?.items) return old
        return {
          ...old,
          items: old.items.map((item: any) =>
            item.id === txId
              ? { ...item, category_id: categoryId, category: categoryName || item.category }
              : item
          )
        }
      })

      return { previousData }
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousData) {
        context.previousData.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['transaction-stats'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    }
  })
}
