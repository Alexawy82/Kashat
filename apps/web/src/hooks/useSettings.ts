import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// ==================== APP SETTINGS ====================

export interface AppSettings {
  // Transaction defaults
  recurring_tolerance?: number
  recurring_default_view?: string
  recurring_show_annual?: boolean
  recurring_sparkline_period?: number
  tx_default_sort_by?: string
  tx_default_sort_dir?: string
  tx_include_transfers_default?: boolean
  tx_business_filter_default?: string

  // AI provider configuration
  ai_provider?: string  // auto, openai, lmstudio, local

  // OpenAI settings
  ai_openai_api_key?: string
  ai_openai_base_url?: string
  ai_openai_model?: string

  // LM Studio settings
  ai_lmstudio_base_url?: string
  ai_lmstudio_model?: string

  // Model overrides for specific tasks
  ai_model_categorize?: string
  ai_model_merchant?: string
  ai_model_anomaly?: string

  // Timeout and retry settings (best practices 2025)
  ai_timeout?: number  // Request timeout in seconds
  ai_connect_timeout?: number  // Connection timeout
  ai_max_retries?: number  // Number of retries on failure
  ai_retry_min_wait?: number  // Minimum wait between retries
  ai_retry_max_wait?: number  // Maximum wait between retries
  ai_retry_jitter?: boolean  // Add randomness to retry delays
  ai_max_concurrency?: number  // Maximum concurrent requests
  ai_temperature?: number  // Model temperature (0-1)

  // AI behavior
  ai_auto_categorize_on_import?: boolean
  ai_auto_categorize_min_conf?: number
  ai_auto_create_rules?: boolean
  ai_auto_rule_min_conf?: number
  ai_anomaly_min_conf?: number
  ai_debug?: boolean  // Log prompts and responses

  // AI processing queue controls
  ai_processing_paused?: boolean
  ai_batch_size?: number
  ai_batch_delay_ms?: number
  ai_max_concurrent_jobs?: number
  ai_job_timeout_minutes?: number
  ai_auto_start_on_import?: boolean

  // Dashboard
  dashboard_default_period?: string
  dashboard_show_ai?: boolean

  // Runtime
  realtime_enabled?: boolean
  duckdb_threads?: number
}

export function useAppSettings() {
  return useQuery({
    queryKey: ['app-settings'],
    queryFn: async () => {
      const { data, error } = await client.get<AppSettings>('/api/settings')
      if (error) throw new Error('Failed to fetch settings')
      return data || {}
    }
  })
}

export function useSaveSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (settings: Partial<AppSettings>) => {
      const { data, error } = await client.post<AppSettings>('/api/settings', {
        body: settings
      })
      if (error) throw new Error('Failed to save settings')
      return data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['app-settings'], data)
    }
  })
}

export function useAISettings() {
  return useQuery({
    queryKey: ['ai-settings'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/settings/ai')
      if (error) throw new Error('Failed to fetch AI settings')
      return data as any
    }
  })
}

export function useSaveAISettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (settings: Partial<Pick<AppSettings,
      | 'ai_provider'
      | 'ai_openai_api_key'
      | 'ai_openai_base_url'
      | 'ai_openai_model'
      | 'ai_lmstudio_base_url'
      | 'ai_lmstudio_model'
      | 'ai_timeout'
      | 'ai_max_retries'
      | 'ai_retry_jitter'
      | 'ai_max_concurrency'
      | 'ai_temperature'
      | 'ai_auto_categorize_on_import'
      | 'ai_auto_categorize_min_conf'
      | 'ai_debug'
    >>) => {
      const { data, error } = await client.put('/api/settings/ai', {
        body: settings
      })
      if (error) throw new Error('Failed to save AI settings')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-settings'] })
      queryClient.invalidateQueries({ queryKey: ['app-settings'] })
      queryClient.invalidateQueries({ queryKey: ['ai-status'] })
    }
  })
}

// ==================== DATA STATS ====================

export function useDataStats() {
  return useQuery({
    queryKey: ['data-stats'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/admin/data/stats')
      if (error) throw new Error('Failed to fetch data stats')
      return (data as any)?.stats || {}
    }
  })
}

// ==================== MERCHANT MEMORY ====================

export function useMerchantMemory() {
  return useQuery({
    queryKey: ['merchant-memory'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/merchant-memory/learned-mappings')
      if (error) return []
      return (data as any)?.mappings || []
    }
  })
}

export function useDeleteMerchantMemory() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (pattern: string) => {
      const { error } = await client.delete('/api/ai/merchant-memory/learned-mappings', {
        params: { query: { pattern } }
      })
      if (error) throw new Error('Failed to delete mapping')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['merchant-memory'] })
    }
  })
}

// ==================== BACKUP & RESTORE ====================

export function useCreateBackup() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/admin/data/backup')
      if (error) throw new Error('Failed to create backup')
      return data as any
    }
  })
}

export function useOptimizeDatabase() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/admin/data/optimize')
      if (error) throw new Error('Failed to optimize database')
      return data
    }
  })
}

// ==================== DANGER ZONE ====================

export function useResetAI() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/admin/data/reset-ai')
      if (error) throw new Error('Failed to reset AI')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['data-stats'] })
    }
  })
}

export function useFactoryReset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/admin/data/factory-reset', {
        body: { confirm: 'FACTORY RESET' }
      })
      if (error) throw new Error('Failed to factory reset')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries()
    }
  })
}

export function useWipeAllData() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/admin/data/wipe-all', {
        body: { confirm: 'WIPE ALL' }
      })
      if (error) throw new Error('Failed to wipe data')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries()
    }
  })
}

// ==================== EXPORT ====================

export function useExportCSV() {
  return useMutation({
    mutationFn: async (params: {
      startDate?: string
      endDate?: string
      onlyBusiness?: boolean
      includeTransfers?: boolean
    }) => {
      // Trigger download via window.location
      const query = new URLSearchParams()
      if (params.startDate) query.set('from', params.startDate)
      if (params.endDate) query.set('to', params.endDate)
      if (params.onlyBusiness) query.set('onlyBusiness', 'true')
      if (params.includeTransfers) query.set('includeTransfers', 'true')

      const baseUrl = process.env.NEXT_PUBLIC_API_BASE || ''
      window.location.href = `${baseUrl}/api/export/csv?${query.toString()}`

      return { exported: true }
    }
  })
}

// ==================== AI CATEGORY MAPPING ====================

export function useAIMappings() {
  return useQuery({
    queryKey: ['ai-mappings'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/admin/ai-mapping')
      if (error) return []
      return (data as any)?.mappings || []
    }
  })
}

export function useAddAIMapping() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      provider?: string
      source_label: string
      category_id: string
    }) => {
      const { data, error } = await client.post('/api/admin/ai-mapping', {
        body: params
      })
      if (error) throw new Error('Failed to add mapping')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-mappings'] })
    }
  })
}

export function useDeleteAIMapping() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: { provider?: string; source_label: string }) => {
      const { error } = await client.delete('/api/admin/ai-mapping', {
        params: { query: params }
      })
      if (error) throw new Error('Failed to delete mapping')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-mappings'] })
    }
  })
}
