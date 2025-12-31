import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// Types
export interface IncomeSource {
  id: string
  name: string
  type: 'salary' | 'side_income' | 'investment' | 'transfer' | 'refund' | 'other'
  avg_amount: number
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'irregular' | string
  confidence: number
  is_active?: boolean
  last_date?: string
  occurrence_count?: number
  pattern?: string
}

export interface CategorySuggestion {
  category_id: string
  category_name: string
  suggested_limit: number
  avg_spending: number
  max_spending: number
  trend: 'increasing' | 'stable' | 'decreasing'
  is_committed: boolean
  recurring_amount: number
  confidence: number
  rationale: string
}

export interface BudgetSuggestion {
  id: string
  name: string
  period: string
  total_income: number
  suggested_total: number
  savings_target: number
  savings_percent: number
  categories: CategorySuggestion[]
  created_at: string
}

export interface PaceWarning {
  category_id: string
  category_name: string
  status: 'on_track' | 'at_risk' | 'will_exceed' | 'exceeded'
  spent: number
  limit: number
  pace_percent: number
  expected_by_end: number
  days_in_period: number
  days_elapsed: number
  days_remaining: number
  message: string
}

export interface BudgetPace {
  budget_id: string
  overall_status: 'on_track' | 'at_risk' | 'will_exceed' | 'exceeded'
  overall_pace_percent: number
  total_spent: number
  total_limit: number
  warnings: PaceWarning[]
  period_start: string
  period_end: string
}

export interface CommittedFlexibleBreakdown {
  committed: Array<{
    id: string
    category_name: string
    amount_limit: number
    linked_recurring_id?: string
    spent: number
  }>
  flexible: Array<{
    id: string
    category_name: string
    amount_limit: number
    spent: number
  }>
  totals: {
    committed_limit: number
    committed_spent: number
    flexible_limit: number
    flexible_spent: number
  }
}

export interface BudgetSettings {
  id: string
  include_irregular_income: boolean
  pace_warning_threshold: number
  savings_goal_percent: number
  auto_suggest_enabled: boolean
  suggestion_frequency: 'weekly' | 'monthly' | 'on_demand'
}

// Hooks

/**
 * Fetch detected income sources
 */
export function useIncome() {
  return useQuery({
    queryKey: ['budget-intelligence', 'income'],
    queryFn: async () => {
      const { data, error } = await client.get<{ sources: IncomeSource[], total_monthly: number }>('/api/budgets/income')
      if (error) throw error
      return data?.sources || []
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Detect and save income sources from transactions
 */
export function useDetectIncome() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post<{
        detected: number
        sources: IncomeSource[]
        total_monthly: number
      }>('/api/budgets/income/detect')
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-intelligence', 'income'] })
    },
  })
}

/**
 * Update an income source
 */
export function useUpdateIncome() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      sourceId,
      updates,
    }: {
      sourceId: string
      updates: Partial<IncomeSource>
    }) => {
      const { data, error } = await client.put(`/api/budgets/income/${sourceId}`, {
        body: updates,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-intelligence', 'income'] })
    },
  })
}

/**
 * Generate smart budget suggestion based on income and spending patterns
 */
export function useBudgetSuggestion(savingsTarget?: number) {
  return useQuery({
    queryKey: ['budget-intelligence', 'suggestion', savingsTarget],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (savingsTarget !== undefined) {
        params.set('savings_target', savingsTarget.toString())
      }
      const url = `/api/budgets/suggest${params.toString() ? `?${params}` : ''}`
      const { data, error } = await client.get<BudgetSuggestion>(url)
      if (error) throw error
      return data
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * Get per-category budget suggestions
 */
export function useCategorySuggestions() {
  return useQuery({
    queryKey: ['budget-intelligence', 'category-suggestions'],
    queryFn: async () => {
      const { data, error } = await client.get<CategorySuggestion[]>(
        '/api/budgets/suggest/categories'
      )
      if (error) throw error
      return data || []
    },
    staleTime: 10 * 60 * 1000,
  })
}

/**
 * Apply a budget suggestion to create an actual budget
 */
export function useApplySuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      suggestionId,
      customName,
    }: {
      suggestionId: string
      customName?: string
    }) => {
      const { data, error } = await client.post('/api/budgets/suggest/apply', {
        body: { suggestion_id: suggestionId, custom_name: customName },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['budget-intelligence'] })
    },
  })
}

/**
 * Get pace warnings for a budget
 */
export function useBudgetPace(budgetId: string) {
  return useQuery({
    queryKey: ['budget-intelligence', 'pace', budgetId],
    queryFn: async () => {
      const { data, error } = await client.get<BudgetPace>(`/api/budgets/${budgetId}/pace`)
      if (error) throw error
      return data
    },
    enabled: !!budgetId,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
  })
}

/**
 * Save a pace snapshot for historical tracking
 */
export function useSavePaceSnapshot() {
  return useMutation({
    mutationFn: async (budgetId: string) => {
      const { data, error } = await client.post(`/api/budgets/${budgetId}/pace/snapshot`)
      if (error) throw error
      return data
    },
  })
}

/**
 * Get committed vs flexible spending breakdown
 */
export function useBudgetBreakdown(budgetId: string) {
  return useQuery({
    queryKey: ['budget-intelligence', 'breakdown', budgetId],
    queryFn: async () => {
      const { data, error } = await client.get<CommittedFlexibleBreakdown>(
        `/api/budgets/${budgetId}/breakdown`
      )
      if (error) throw error
      return data
    },
    enabled: !!budgetId,
  })
}

/**
 * Get budget-related AI insights
 */
export function useBudgetInsights(limit = 6) {
  return useQuery({
    queryKey: ['budget-intelligence', 'insights', limit],
    queryFn: async () => {
      const { data, error } = await client.get<{ insights: any[] }>(`/api/budgets/insights?limit=${limit}`)
      if (error) return []
      return data?.insights || []
    },
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Get budget settings
 */
export function useBudgetSettings() {
  return useQuery({
    queryKey: ['budget-intelligence', 'settings'],
    queryFn: async () => {
      const { data, error } = await client.get<BudgetSettings>('/api/budgets/settings')
      if (error) throw error
      return data
    },
  })
}

/**
 * Update budget settings
 */
export function useUpdateBudgetSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (settings: Partial<BudgetSettings>) => {
      const { data, error } = await client.put('/api/budgets/settings', {
        body: settings,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-intelligence', 'settings'] })
    },
  })
}

// Composite hooks for complex UI scenarios

/**
 * Hook combining income and suggestion for the Smart Budget Wizard
 */
export function useSmartBudgetWizard() {
  const income = useIncome()
  const detectIncome = useDetectIncome()
  const suggestion = useBudgetSuggestion()
  const applySuggestion = useApplySuggestion()

  const totalMonthlyIncome = income.data?.reduce((sum, src) => {
    if (!src.is_active) return sum
    switch (src.frequency) {
      case 'weekly':
        return sum + src.avg_amount * 4.33
      case 'biweekly':
        return sum + src.avg_amount * 2.17
      case 'monthly':
        return sum + src.avg_amount
      case 'irregular':
        return sum + src.avg_amount * 0.5 // Conservative estimate
      default:
        return sum + src.avg_amount
    }
  }, 0) || 0

  return {
    income: income.data || [],
    incomeLoading: income.isLoading,
    totalMonthlyIncome,
    detectIncome: detectIncome.mutateAsync,
    isDetecting: detectIncome.isPending,
    suggestion: suggestion.data,
    suggestionLoading: suggestion.isLoading,
    applySuggestion: applySuggestion.mutateAsync,
    isApplying: applySuggestion.isPending,
    refetch: () => {
      income.refetch()
      suggestion.refetch()
    },
  }
}

/**
 * Hook for budget pace monitoring with status colors
 */
export function useBudgetPaceWithStatus(budgetId: string) {
  const pace = useBudgetPace(budgetId)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on_track':
        return 'green'
      case 'at_risk':
        return 'yellow'
      case 'will_exceed':
        return 'orange'
      case 'exceeded':
        return 'red'
      default:
        return 'gray'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'on_track':
        return 'check-circle'
      case 'at_risk':
        return 'alert-circle'
      case 'will_exceed':
        return 'alert-triangle'
      case 'exceeded':
        return 'x-circle'
      default:
        return 'help-circle'
    }
  }

  return {
    ...pace,
    getStatusColor,
    getStatusIcon,
    hasWarnings: (pace.data?.warnings?.length ?? 0) > 0,
    criticalWarnings: pace.data?.warnings?.filter(
      (w) => w.status === 'will_exceed' || w.status === 'exceeded'
    ) || [],
  }
}
