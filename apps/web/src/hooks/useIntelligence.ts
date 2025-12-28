import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// Financial health assessment
export function useFinancialHealth(account_id?: string) {
  return useQuery({
    queryKey: ['financial-health', account_id],
    queryFn: async () => {
      const { data, error } = await client.get('/api/intelligence/health', {
        params: { query: { account_id } }
      })
      if (error) throw new Error('Failed to fetch financial health')
      return data as any
    },
  })
}

// Spending behavior analysis
export function useSpendingBehavior(account_id?: string) {
  return useQuery({
    queryKey: ['spending-behavior', account_id],
    queryFn: async () => {
      const { data, error } = await client.get('/api/intelligence/behavior', {
        params: { query: { account_id } }
      })
      if (error) throw new Error('Failed to fetch spending behavior')
      return data as any
    },
  })
}

// Personalized insights
export function useInsights(params?: { account_id?: string; limit?: number }) {
  return useQuery({
    queryKey: ['insights', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/intelligence/insights', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch insights')
      return data as any
    },
  })
}

// Intelligence feed (unified stream)
export function useIntelligenceFeed(params?: {
  account_id?: string
  limit?: number
  filters?: {
    include_anomalies?: boolean
    include_trends?: boolean
    include_recommendations?: boolean
    include_alerts?: boolean
    min_priority?: string
  }
}) {
  return useQuery({
    queryKey: ['intelligence-feed', params],
    queryFn: async () => {
      const { data, error } = await client.post('/api/intelligence/feed', {
        params: { query: { account_id: params?.account_id, limit: params?.limit } },
        body: params?.filters || {
          include_anomalies: true,
          include_trends: true,
          include_recommendations: true,
          include_alerts: true,
          min_priority: 'low'
        }
      })
      if (error) throw new Error('Failed to fetch intelligence feed')
      return data as any
    },
  })
}

// Subscription detection
export function useSubscriptions(account_id?: string) {
  return useQuery({
    queryKey: ['subscriptions', account_id],
    queryFn: async () => {
      const { data, error } = await client.get('/api/intelligence/subscriptions', {
        params: { query: { account_id } }
      })
      if (error) throw new Error('Failed to fetch subscriptions')
      return data as any
    },
  })
}

// AI Rule suggestions
export function useRuleSuggestions(params?: {
  min_occurrences?: number
  min_confidence?: number
}) {
  return useQuery({
    queryKey: ['rule-suggestions', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/intelligence/rules/suggest', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch rule suggestions')
      return data as any
    },
  })
}

// AI Recurring detection
export function useRecurringDetection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: {
      min_occurrences?: number
      confidence_threshold?: number
    }) => {
      const { data, error } = await client.post('/api/intelligence/recurring/detect', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to detect recurring transactions')
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    }
  })
}

// AI Transfer suggestions
export function useTransferSuggestions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params?: {
      date_tolerance_days?: number
      amount_tolerance_pct?: number
      min_confidence?: number
    }) => {
      const { data, error } = await client.post('/api/intelligence/transfers/suggest', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to detect transfers')
      return data as any
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfers'] })
    }
  })
}
