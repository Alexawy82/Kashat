import { useQuery, useMutation } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// Dashboard analytics hook
export function useAnalyticsDashboard(params?: {
  start_date?: string
  end_date?: string
  account_id?: string
  include_ai?: boolean
}) {
  return useQuery({
    queryKey: ['analytics-dashboard', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/dashboard', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch dashboard analytics')
      return data as any
    },
    staleTime: 60 * 1000, // 1 minute
  })
}

// Monthly analytics hook
export function useAnalyticsMonthly(params?: {
  start_date?: string
  end_date?: string
  account_id?: string
}) {
  return useQuery({
    queryKey: ['analytics-monthly', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/monthly', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch monthly analytics')
      return data as any
    },
  })
}

// Category monthly breakdown
export function useAnalyticsCategoryMonthly(params?: {
  start_date?: string
  end_date?: string
  account_id?: string
}) {
  return useQuery({
    queryKey: ['analytics-category-monthly', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/category-monthly', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch category analytics')
      return data as any
    },
  })
}

// Top merchants
export function useAnalyticsMerchants(params?: {
  start_date?: string
  end_date?: string
  account_id?: string
  limit?: number
}) {
  return useQuery({
    queryKey: ['analytics-merchants', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/merchants', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch merchant analytics')
      return data as any
    },
  })
}

// Analytics summary
export function useAnalyticsSummary(params?: {
  from?: string
  to?: string
  includeTransfers?: boolean
}) {
  return useQuery({
    queryKey: ['analytics-summary', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/summary', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch analytics summary')
      return data as any
    },
  })
}

// AI Spending patterns
export function useSpendingPatterns(params?: {
  start_date?: string
  end_date?: string
  account_id?: string
}) {
  return useQuery({
    queryKey: ['ai-spending-patterns', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/spending-patterns', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch spending patterns')
      return data as any
    },
  })
}

// AI Trends
export function useAITrends(params?: {
  start_date?: string
  end_date?: string
  account_id?: string
}) {
  return useQuery({
    queryKey: ['ai-trends', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/trends', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch AI trends')
      return data as any
    },
  })
}

// AI Anomalies
export function useAnomalies(params?: {
  days_lookback?: number
  account_id?: string
}) {
  return useQuery({
    queryKey: ['ai-anomalies', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/anomalies', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch anomalies')
      return data as any
    },
  })
}

// AI Spending Forecast
export function useSpendingForecast(params?: {
  category?: string
  forecast_months?: number
  account_id?: string
}) {
  return useQuery({
    queryKey: ['ai-spending-forecast', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/forecasts/spending', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch spending forecast')
      return data as any
    },
  })
}

// AI Cashflow Projection
export function useCashflowProjection(params?: {
  forecast_months?: number
  account_id?: string
}) {
  return useQuery({
    queryKey: ['ai-cashflow-projection', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/forecasts/cashflow', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch cashflow projection')
      return data as any
    },
  })
}

// Predictive insights
export function usePredictiveInsights(params?: {
  account_id?: string
  include_read?: boolean
}) {
  return useQuery({
    queryKey: ['predictive-insights', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/predictive/insights', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch predictive insights')
      return data as any
    },
  })
}

// ==================== ADDITIONAL ANALYTICS HOOKS ====================

// Recurring analytics
export function useRecurringAnalytics(params?: {
  account_id?: string
}) {
  return useQuery({
    queryKey: ['analytics-recurring', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/recurring', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch recurring analytics')
      return data as {
        total_monthly_recurring: number
        categories: Array<{ name: string; amount: number; count: number }>
        upcoming: Array<{ merchant: string; amount: number; next_date: string }>
      }
    },
  })
}

// Income forecast
export function useIncomeForecast(params?: {
  forecast_months?: number
  account_id?: string
}) {
  return useQuery({
    queryKey: ['income-forecast', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/forecasts/income', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch income forecast')
      return data as {
        current_monthly_income: number
        predicted_monthly_income: number
        confidence: number
        trend: string
        monthly_projections: Array<{ month: string; amount: number }>
      }
    },
  })
}

// Cashflow forecast (predictive version)
export function useCashflowForecast(params?: {
  months?: number
  account_id?: string
}) {
  return useQuery({
    queryKey: ['cashflow-forecast', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/predictive/cashflow-forecast', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch cashflow forecast')
      return data as {
        current_balance: number
        projected_balance: number
        monthly_projections: Array<{
          month: string
          income: number
          expenses: number
          balance: number
        }>
        risk_level: string
      }
    },
  })
}

// Predictive patterns
export function usePredictivePatterns(params?: {
  account_id?: string
}) {
  return useQuery({
    queryKey: ['predictive-patterns', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/predictive/patterns', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to fetch predictive patterns')
      return data as {
        spending_patterns: Array<{
          category: string
          avg_amount: number
          frequency: string
          trend: string
        }>
        income_patterns: Array<{
          source: string
          avg_amount: number
          frequency: string
        }>
        anomaly_likelihood: number
      }
    },
  })
}

// Comprehensive AI insights
export function useComprehensiveInsights() {
  return useMutation({
    mutationFn: async (params?: { account_id?: string; period?: string }) => {
      const { data, error } = await client.post('/api/analytics/ai/comprehensive-insights', {
        body: params || {}
      })
      if (error) throw new Error('Failed to fetch comprehensive insights')
      return data as {
        summary: string
        key_insights: string[]
        recommendations: string[]
        risk_factors: string[]
      }
    }
  })
}

// AI dashboard summary
export function useAIDashboardSummary(params?: {
  account_id?: string
}) {
  return useQuery({
    queryKey: ['ai-dashboard-summary', params],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/ai/dashboard-summary', {
        params: { query: params }
      })
      if (error) return null
      return data as {
        health_score: number
        spending_trend: string
        savings_rate: number
        alerts: Array<{ type: string; message: string; severity: string }>
      }
    },
  })
}
