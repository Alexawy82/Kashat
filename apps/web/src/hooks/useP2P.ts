import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// ==================== TYPES ====================

export interface P2PStats {
  total_p2p_transactions: number
  by_service: Record<string, { count: number; total_amount: number }>
  by_direction: Record<string, { count: number; total_amount: number }>
  top_counterparties: Array<{
    name: string
    transaction_count: number
    total_sent: number
    total_received: number
  }>
}

export interface Counterparty {
  id: string
  name: string
  aliases: string[]
  total_sent: number
  total_received: number
  net_flow: number
  transaction_count: number
  first_seen: string
  last_seen: string
  is_recurring: boolean
}

export interface CounterpartyTransaction {
  id: string
  tx_id: string
  service: string
  counterparty_raw: string
  counterparty_normalized: string
  direction: string
  amount: number
  posted_at: string
  description_norm: string
  transaction_type?: string
  counterparty_type?: string
}

export interface EnrichmentStats {
  total: number
  enriched: number
  classified: number
  unclassified: number
  by_transaction_type: Record<string, { count: number; total_amount: number }>
  by_counterparty_type: Record<string, number>
  by_service_and_type: Array<{
    service: string
    transaction_type: string
    count: number
  }>
}

export interface DetectionResult {
  status: string
  total_detected: number
  by_service: Record<string, number>
  new_counterparties: number
}

// ==================== CORE DATA HOOKS ====================

/**
 * Get P2P statistics (total, by service, by direction, top counterparties)
 */
export function useP2PStats() {
  return useQuery({
    queryKey: ['p2p-stats'],
    queryFn: async () => {
      const { data, error } = await client.get<P2PStats>('/api/p2p/stats')
      if (error) throw new Error('Failed to fetch P2P stats')
      return data
    },
  })
}

/**
 * Get list of counterparties with optional filters
 */
export function useCounterparties(params?: {
  recurring_only?: boolean
  min_transactions?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['counterparties', params],
    queryFn: async () => {
      const { data, error } = await client.get<{ counterparties: Counterparty[]; count: number }>(
        '/api/p2p/counterparties',
        {
          params: {
            query: {
              recurring_only: params?.recurring_only,
              min_transactions: params?.min_transactions,
              limit: params?.limit || 100,
            },
          },
        }
      )
      if (error) throw new Error('Failed to fetch counterparties')
      return data?.counterparties || []
    },
  })
}

/**
 * Get transactions for a specific counterparty
 */
export function useCounterpartyTransactions(counterpartyId: string | null) {
  return useQuery({
    queryKey: ['counterparty-transactions', counterpartyId],
    queryFn: async () => {
      if (!counterpartyId) return []
      const { data, error } = await client.get<{ transactions: CounterpartyTransaction[]; count: number }>(
        `/api/p2p/counterparties/${counterpartyId}/transactions`
      )
      if (error) throw new Error('Failed to fetch counterparty transactions')
      return data?.transactions || []
    },
    enabled: !!counterpartyId,
  })
}

/**
 * Get enrichment statistics
 */
export function useEnrichmentStats() {
  return useQuery({
    queryKey: ['enrichment-stats'],
    queryFn: async () => {
      const { data, error } = await client.get<EnrichmentStats>('/api/p2p/enrichment-stats')
      if (error) throw new Error('Failed to fetch enrichment stats')
      return data
    },
  })
}

// ==================== DETECTION & ENRICHMENT HOOKS ====================

/**
 * Run P2P detection on transactions
 */
export function useDetectP2P() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { use_ai?: boolean; limit?: number; skip_existing?: boolean }) => {
      const { data, error } = await client.post<DetectionResult>('/api/p2p/detect', {
        params: {
          query: {
            use_ai: params?.use_ai ?? false,
            limit: params?.limit ?? 1000,
            skip_existing: params?.skip_existing ?? true,
          },
        },
      })
      if (error) throw new Error('Failed to run P2P detection')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['p2p-stats'] })
      queryClient.invalidateQueries({ queryKey: ['counterparties'] })
      queryClient.invalidateQueries({ queryKey: ['enrichment-stats'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
    },
  })
}

/**
 * Run AI enrichment on P2P transactions
 */
export function useEnrichP2P() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: { service_filter?: string; only_unclassified?: boolean; limit?: number }) => {
      const { data, error } = await client.post<{ status: string; enriched: number; errors: number }>(
        '/api/p2p/enrich',
        {
          params: {
            query: {
              service_filter: params?.service_filter,
              only_unclassified: params?.only_unclassified ?? true,
              limit: params?.limit ?? 50,
            },
          },
        }
      )
      if (error) throw new Error('Failed to run P2P enrichment')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['p2p-stats'] })
      queryClient.invalidateQueries({ queryKey: ['counterparties'] })
      queryClient.invalidateQueries({ queryKey: ['enrichment-stats'] })
    },
  })
}

// ==================== COUNTERPARTY MANAGEMENT HOOKS ====================

/**
 * Merge two counterparties (consolidate duplicates)
 */
export function useMergeCounterparties() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ sourceId, targetId }: { sourceId: string; targetId: string }) => {
      const { data, error } = await client.post<{ status: string; message: string }>(
        '/api/p2p/merge-counterparties',
        {
          params: {
            query: {
              source_id: sourceId,
              target_id: targetId,
            },
          },
        }
      )
      if (error) throw new Error('Failed to merge counterparties')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['counterparties'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-stats'] })
      queryClient.invalidateQueries({ queryKey: ['counterparty-transactions'] })
    },
  })
}


/**
 * Get P2P transactions that appear recurring but aren't linked to recurring workflow
 */
export function useUnlinkedRecurring() {
  return useQuery({
    queryKey: ['unlinked-recurring'],
    queryFn: async () => {
      const { data, error } = await client.get<{
        candidates: Array<{
          counterparty: string
          service: string
          transaction_count: number
          avg_amount: number
          first_date: string
          last_date: string
        }>
      }>('/api/p2p/unlinked-recurring')
      if (error) throw new Error('Failed to fetch unlinked recurring')
      return data?.candidates || []
    },
  })
}

/**
 * Link a P2P transaction to a recurring series
 */
export function useLinkToRecurring() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ p2pId, recurringSeriesId }: { p2pId: string; recurringSeriesId: string }) => {
      const { data, error } = await client.post<{ status: string; message: string }>(
        '/api/p2p/link-recurring',
        {
          params: {
            query: {
              p2p_id: p2pId,
              recurring_series_id: recurringSeriesId,
            },
          },
        }
      )
      if (error) throw new Error('Failed to link to recurring')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['counterparties'] })
      queryClient.invalidateQueries({ queryKey: ['unlinked-recurring'] })
      queryClient.invalidateQueries({ queryKey: ['recurring-confirmed'] })
    },
  })
}

// ==================== LEGACY HOOKS (from useAutomation) ====================
// These are re-exported for convenience, but the originals remain in useAutomation.ts

/**
 * Get P2P summary grouped by provider + counterparty
 * This uses the legacy /api/p2p/summary endpoint
 */
export function useP2PSummary(params?: { provider?: string; limit?: number }) {
  return useQuery({
    queryKey: ['p2p-summary', params?.provider, params?.limit],
    queryFn: async () => {
      const { data, error } = await client.get<
        Array<{
          provider: string
          counterparty: string
          count: number
          total_out: number
          total_in: number
          net: number
          first_date: string
          last_date: string
        }>
      >('/api/p2p/summary', {
        params: {
          query: {
            provider: params?.provider,
            limit: params?.limit ?? 25,
          },
        },
      })
      if (error) return []
      return data || []
    },
  })
}
