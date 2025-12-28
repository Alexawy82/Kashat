import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  is_liquid: boolean
  auto_update: boolean
  update_source?: string
  last_updated?: string
  update_reminder?: string
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
  linked_asset_id?: string
  start_date?: string
  expected_payoff_date?: string
  lender?: string
  account_number?: string
  notes?: string
  auto_calculate: boolean
  linked_account_id?: string
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
  manual_assets: number
  total_liabilities: number
  net_worth: number
  asset_breakdown: Record<string, number>
  liability_breakdown: Record<string, number>
  assets: Asset[]
  liabilities: Liability[]
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
      const url = assetType ? `/api/assets?asset_type=${assetType}` : '/api/assets'
      const { data, error } = await client.get<Asset[]>(url)
      if (error) throw new Error('Failed to fetch assets')
      return data ?? []
    },
  })
}

/**
 * Get asset summary by type
 */
export function useAssetSummary() {
  return useQuery({
    queryKey: ['assets', 'summary'],
    queryFn: async () => {
      const { data, error } = await client.get<AssetSummary>('/api/assets/summary')
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
      const { data, error } = await client.post<Asset>('/api/assets', { body: asset })
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
      const { data, error } = await client.put<Asset>(`/api/assets/${id}`, { body: updates })
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
      const { error } = await client.delete(`/api/assets/${id}`)
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
      const { data, error } = await client.post<Asset>(`/api/assets/${id}/update-value?value=${value}`)
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
      const url = liabilityType ? `/api/liabilities?liability_type=${liabilityType}` : '/api/liabilities'
      const { data, error } = await client.get<Liability[]>(url)
      if (error) throw new Error('Failed to fetch liabilities')
      return data ?? []
    },
  })
}

/**
 * Create a new liability
 */
export function useCreateLiability() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (liability: LiabilityCreate) => {
      const { data, error } = await client.post<Liability>('/api/liabilities', { body: liability })
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
      const { data, error } = await client.put<Liability>(`/api/liabilities/${id}`, { body: updates })
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
      const { error } = await client.delete(`/api/liabilities/${id}`)
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
      const { data, error } = await client.get<MetalSpotPrices>('/api/metals/spot')
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
      const { data, error } = await client.post<{ updated: number; spot_prices: Record<string, number> }>('/api/metals/refresh')
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
