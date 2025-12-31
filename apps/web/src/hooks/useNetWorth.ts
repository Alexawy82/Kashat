import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// ==================== TYPES ====================

export interface Asset {
  id: string
  name: string
  asset_type: 'real_estate' | 'vehicle' | 'precious_metal' | 'investment' | 'business' | 'other'
  subtype?: string
  current_value: number
  purchase_price?: number
  purchase_date?: string
  weight_oz?: number
  weight_unit?: string
  spot_price?: number
  premium_paid?: number
  metal_type?: string
  address?: string
  property_type?: string
  year?: number
  make?: string
  model?: string
  vin?: string
  institution?: string
  account_type?: string
  valuation_method?: string
  monthly_revenue?: number
  multiplier?: number
  notes?: string
  is_liquid?: boolean
  auto_update?: boolean
  update_source?: string
  last_updated?: string
  update_reminder?: string
  // Intelligence fields
  details?: Record<string, any> | string
  linked_recurring_id?: string
  linked_liability_id?: string
  suggestion_id?: string
  enrichment_source?: string
  enrichment_data?: Record<string, any> | string
  last_enriched_at?: string
  auto_refresh?: boolean
  milestones_json?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface AssetCreate {
  name: string
  asset_type: Asset['asset_type']
  subtype?: string
  current_value: number
  purchase_price?: number
  purchase_date?: string
  weight_oz?: number
  weight_unit?: string
  metal_type?: string
  premium_paid?: number
  address?: string
  property_type?: string
  year?: number
  make?: string
  model?: string
  vin?: string
  institution?: string
  account_type?: string
  ticker?: string
  shares?: number
  cost_basis?: number
  valuation_method?: string
  monthly_revenue?: number
  multiplier?: number
  notes?: string
  is_liquid?: boolean
  auto_update?: boolean
  update_source?: string
  update_reminder?: string
}

export interface Liability {
  id: string
  name: string
  liability_type: 'mortgage' | 'auto_loan' | 'personal_loan' | 'student_loan' | 'credit_card' | 'other'
  original_amount?: number
  current_balance: number
  interest_rate?: number
  monthly_payment?: number
  term_months?: number
  linked_asset_id?: string
  start_date?: string
  expected_payoff_date?: string
  lender?: string
  account_number?: string
  notes?: string
  auto_calculate?: boolean
  linked_account_id?: string
  // Intelligence fields
  linked_recurring_id?: string
  suggestion_id?: string
  auto_calculate_balance?: boolean
  milestones_json?: string
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

export interface LiabilityCreate {
  name: string
  liability_type: Liability['liability_type']
  original_amount?: number
  current_balance: number
  interest_rate?: number
  monthly_payment?: number
  linked_asset_id?: string
  start_date?: string
  expected_payoff_date?: string
  lender?: string
  account_number?: string
  notes?: string
  auto_calculate?: boolean
  linked_account_id?: string
}

export interface AssetSummary {
  total_value: number
  by_type: Record<string, number>
  count_by_type: Record<string, number>
}

export interface MetalSpotPrices {
  gold?: number
  silver?: number
  platinum?: number
  palladium?: number
  as_of: string
  source: string
}

export interface CompleteNetWorth {
  total_assets: number
  bank_accounts: number
  manual_assets?: number
  total_liabilities: number
  net_worth: number
  breakdown: {
    bank_accounts?: { total: number; accounts: Array<{ id: string; name: string; account_type: string; balance: number }> }
    assets: Record<string, { total: number; items: Asset[] }>
    liabilities: Record<string, { total: number; items: Liability[] }>
  }
  asset_breakdown?: Record<string, number>
  liability_breakdown?: Record<string, number>
  assets: Asset[]
  liabilities: Liability[]
  history?: Array<{ date: string; net_worth: number }>
  as_of: string
}

// ==================== ASSET HOOKS ====================

/**
 * Get all assets, optionally filtered by type
 */
export function useAssets(assetType?: string) {
  return useQuery({
    queryKey: ['assets', assetType],
    queryFn: async () => {
      const url = assetType ? `/api/networth/assets?asset_type=${assetType}` : '/api/networth/assets'
      const { data, error } = await client.get<{ assets: any[] }>(url)
      if (error) throw new Error('Failed to fetch assets')
      // Transform 'type' to 'asset_type' for frontend compatibility
      return (data?.assets ?? []).map(a => ({
        ...a,
        asset_type: a.type || a.asset_type,
      })) as Asset[]
    },
    staleTime: 30000, // Data is fresh for 30 seconds
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData, // Keep showing old data during refetch
  })
}

/**
 * Get asset summary by type
 */
export function useAssetSummary() {
  return useQuery({
    queryKey: ['assets', 'summary'],
    queryFn: async () => {
      const { data, error } = await client.get<AssetSummary>('/api/networth/assets/summary')
      if (error) throw new Error('Failed to fetch asset summary')
      return data
    },
  })
}

/**
 * Create a new asset
 */
export function useCreateAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (asset: AssetCreate) => {
      const { data, error } = await client.post<Asset>('/api/networth/assets', { body: asset })
      if (error) throw new Error('Failed to create asset')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

/**
 * Update an existing asset
 */
export function useUpdateAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, ...updates }: Partial<Asset> & { id: string }) => {
      const { data, error } = await client.put<Asset>(`/api/networth/assets/${id}`, { body: updates })
      if (error) throw new Error('Failed to update asset')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

/**
 * Delete an asset
 */
export function useDeleteAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await client.delete(`/api/networth/assets/${id}`)
      if (error) throw new Error('Failed to delete asset')
      return { id }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

/**
 * Quick update asset value
 */
export function useUpdateAssetValue() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, value }: { id: string; value: number }) => {
      const { data, error } = await client.post<Asset>(`/api/networth/assets/${id}/update-value?value=${value}`)
      if (error) throw new Error('Failed to update asset value')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

// ==================== LIABILITY HOOKS ====================

/**
 * Get all liabilities, optionally filtered by type
 */
export function useLiabilities(liabilityType?: string) {
  return useQuery({
    queryKey: ['liabilities', liabilityType],
    queryFn: async () => {
      const url = liabilityType ? `/api/networth/liabilities?liability_type=${liabilityType}` : '/api/networth/liabilities'
      const { data, error } = await client.get<{ liabilities: any[] }>(url)
      if (error) throw new Error('Failed to fetch liabilities')
      // Transform 'type' to 'liability_type' for frontend compatibility
      return (data?.liabilities ?? []).map(l => ({
        ...l,
        liability_type: l.type || l.liability_type,
      })) as Liability[]
    },
    staleTime: 30000, // Data is fresh for 30 seconds
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData, // Keep showing old data during refetch
  })
}

/**
 * Create a new liability
 */
export function useCreateLiability() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (liability: LiabilityCreate) => {
      const { data, error } = await client.post<Liability>('/api/networth/liabilities', { body: liability })
      if (error) throw new Error('Failed to create liability')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['liabilities'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

/**
 * Update an existing liability
 */
export function useUpdateLiability() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, ...updates }: Partial<Liability> & { id: string }) => {
      const { data, error } = await client.put<Liability>(`/api/networth/liabilities/${id}`, { body: updates })
      if (error) throw new Error('Failed to update liability')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['liabilities'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

/**
 * Delete a liability
 */
export function useDeleteLiability() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await client.delete(`/api/networth/liabilities/${id}`)
      if (error) throw new Error('Failed to delete liability')
      return { id }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['liabilities'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

// ==================== NET WORTH HOOKS ====================

/**
 * Get complete net worth with all assets and liabilities
 */
export function useCompleteNetWorth() {
  return useQuery({
    queryKey: ['networth', 'complete'],
    queryFn: async () => {
      const { data, error } = await client.get<CompleteNetWorth>('/api/networth/complete')
      if (error) throw new Error('Failed to fetch complete net worth')
      return data
    },
    staleTime: 30000, // Data is fresh for 30 seconds - prevents refetch flicker
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    placeholderData: keepPreviousData, // Keep showing old data during refetch
  })
}

// ==================== METAL PRICE HOOKS ====================

/**
 * Get current spot prices for precious metals
 */
export function useMetalSpotPrices() {
  return useQuery({
    queryKey: ['metals', 'spot'],
    queryFn: async () => {
      const { data, error } = await client.get<MetalSpotPrices>('/api/networth/metals/spot')
      if (error) throw new Error('Failed to fetch metal prices')
      return data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
  })
}

/**
 * Refresh all metal asset prices
 */
export function useRefreshMetalPrices() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post<{ updated: number; spot_prices: Record<string, number> }>('/api/networth/metals/refresh')
      if (error) throw new Error('Failed to refresh metal prices')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
      queryClient.invalidateQueries({ queryKey: ['metals'] })
    },
  })
}

// ==================== HELPER CONSTANTS ====================

export const ASSET_TYPE_LABELS: Record<Asset['asset_type'], string> = {
  real_estate: 'Real Estate',
  vehicle: 'Vehicle',
  precious_metal: 'Precious Metal',
  investment: 'Investment',
  business: 'Business',
  other: 'Other',
}

export const LIABILITY_TYPE_LABELS: Record<Liability['liability_type'], string> = {
  mortgage: 'Mortgage',
  auto_loan: 'Auto Loan',
  personal_loan: 'Personal Loan',
  student_loan: 'Student Loan',
  credit_card: 'Credit Card',
  other: 'Other',
}

export const METAL_TYPES = ['gold', 'silver', 'platinum', 'palladium'] as const
export type MetalType = typeof METAL_TYPES[number]

export const PROPERTY_TYPES = ['single_family', 'condo', 'townhouse', 'land', 'commercial', 'multi_family'] as const
export const INVESTMENT_ACCOUNT_TYPES = ['401k', 'ira', 'roth_ira', 'brokerage', 'hsa', 'crypto', 'other'] as const

// ==================== NET WORTH INTELLIGENCE ====================

/**
 * Suggestion from the intelligent detection system
 */
export interface NetWorthSuggestion {
  id: string
  type: 'property' | 'vehicle' | 'investment' | 'precious_metal' | 'loan'
  subtype: string
  confidence: number
  source_recurring_id?: string
  source_data: Record<string, any>
  suggested_values: Record<string, any>
  status: 'pending' | 'accepted' | 'dismissed' | 'snoozed'
  snoozed_until?: string
  created_at: string
  recurring_name?: string
  recurring_amount?: number
}

/**
 * Get pending net worth suggestions
 */
export function useNetWorthSuggestions() {
  return useQuery({
    queryKey: ['networth', 'suggestions'],
    queryFn: async () => {
      const { data, error } = await client.get<{ suggestions: NetWorthSuggestion[], count: number }>('/api/networth/suggestions')
      if (error) throw new Error('Failed to fetch suggestions')
      return data
    },
    staleTime: 60000, // 1 minute
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  })
}

/**
 * Get count of pending suggestions (for badge display)
 */
export function useSuggestionCount() {
  return useQuery({
    queryKey: ['networth', 'suggestions', 'count'],
    queryFn: async () => {
      const { data, error } = await client.get<{ count: number }>('/api/networth/suggestions/count')
      if (error) return { count: 0 }
      return data
    },
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
    refetchOnWindowFocus: false,
  })
}

/**
 * Accept a suggestion and create asset/liability
 */
export function useAcceptSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ suggestionId, overrides }: { suggestionId: string, overrides?: Record<string, any> }) => {
      const { data, error } = await client.post(`/api/networth/suggestions/${suggestionId}/accept`, {
        body: overrides || {}
      })
      if (error) throw new Error('Failed to accept suggestion')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networth'] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['liabilities'] })
    },
  })
}

/**
 * Dismiss a suggestion
 */
export function useDismissSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (suggestionId: string) => {
      const { data, error } = await client.post(`/api/networth/suggestions/${suggestionId}/dismiss`)
      if (error) throw new Error('Failed to dismiss suggestion')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networth', 'suggestions'] })
    },
  })
}

/**
 * Snooze a suggestion for later
 */
export function useSnoozeSuggestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ suggestionId, days = 7 }: { suggestionId: string, days?: number }) => {
      const { data, error } = await client.post(`/api/networth/suggestions/${suggestionId}/snooze?days=${days}`)
      if (error) throw new Error('Failed to snooze suggestion')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['networth', 'suggestions'] })
    },
  })
}

// ==================== ENRICHMENT HOOKS ====================

/**
 * Enrich an asset with current market data
 */
export function useEnrichAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (assetId: string) => {
      const { data, error } = await client.post(`/api/networth/assets/${assetId}/enrich`)
      if (error) throw new Error('Failed to enrich asset')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

/**
 * Get stock price
 */
export function useStockPrice(symbol: string) {
  return useQuery({
    queryKey: ['stock', symbol],
    queryFn: async () => {
      const { data, error } = await client.get(`/api/networth/stock/${symbol}`)
      if (error) throw new Error('Failed to fetch stock price')
      return data as {
        symbol: string
        price: number
        change?: number
        change_percent?: number
        name?: string
      }
    },
    enabled: !!symbol,
    staleTime: 60000, // 1 minute
  })
}

/**
 * Decode VIN
 */
export function useDecodeVin() {
  return useMutation({
    mutationFn: async (vin: string) => {
      const { data, error } = await client.post(`/api/networth/vin/decode?vin=${vin}`)
      if (error) throw new Error('Failed to decode VIN')
      return data as {
        vin: string
        year?: string
        make?: string
        model?: string
        trim?: string
        body_class?: string
      }
    },
  })
}

/**
 * Refresh all assets with auto-refresh enabled
 */
export function useRefreshAllAssets() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/networth/refresh-all')
      if (error) throw new Error('Failed to refresh assets')
      return data as { refreshed: number, errors: any[] }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['networth'] })
    },
  })
}

// ==================== SUGGESTION TYPE HELPERS ====================

export const SUGGESTION_TYPE_ICONS: Record<string, string> = {
  property: '🏠',
  vehicle: '🚗',
  investment: '📈',
  precious_metal: '🥇',
  loan: '💳',
}

export const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  property: 'Property / Mortgage',
  vehicle: 'Vehicle / Auto Loan',
  investment: 'Investment Account',
  precious_metal: 'Precious Metal',
  loan: 'Loan',
}

export function formatConfidence(confidence: number): string {
  if (confidence >= 0.9) return 'Very High'
  if (confidence >= 0.75) return 'High'
  if (confidence >= 0.5) return 'Medium'
  return 'Low'
}
