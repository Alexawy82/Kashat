import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// Health check hook
export function useHealthDetailed() {
  return useQuery({
    queryKey: ['health-detailed'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/health/detailed')
      if (error) throw new Error('Failed to fetch health details')
      return data as {
        status: string
        version: string
        environment: string
        uptime: {
          seconds: number
          human: string
          started_at: string
        }
        components: {
          database: {
            status: string
            transaction_count?: number
            import_run_count?: number
            table_count?: number
            db_path?: string
            error?: string
          }
          filesystem: {
            status: string
            data_dir?: string
            exists?: boolean
            writable?: boolean
            free_space_gb?: number
            total_space_gb?: number
            disk_usage_percent?: number
          }
          ai_service: {
            status: string
            api_key_configured?: boolean
            message?: string
          }
          auth_service: {
            status: string
            jwt_secret_configured?: boolean
            auth_module_loaded?: boolean
          }
        }
        timestamp: string
      }
    },
    refetchInterval: 5000, // Poll every 5 seconds
    staleTime: 4000,
  })
}

// AI status hook
export function useAIStatus() {
  return useQuery({
    queryKey: ['ai-status'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/status')
      if (error) return { ok: false, error: 'AI service unavailable' }
      return data as {
        ok: boolean
        provider?: string
        model?: string
        latency_ms?: number
        error?: string
        suggestion?: string
        error_type?: string
        config?: {
          max_retries: number
          timeout: number
        }
        settings?: {
          ai_auto_categorize_on_import: boolean
          ai_auto_categorize_min_conf: number
        }
      }
    },
    refetchInterval: 10000, // Poll every 10 seconds
    staleTime: 9000,
  })
}

// AI ping hook (for testing connection)
export function useAIPing() {
  return useQuery({
    queryKey: ['ai-ping'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/ping')
      if (error) return { ok: false, error: 'AI ping failed' }
      return data as {
        ok: boolean
        provider?: string
        model?: string
        latency_ms?: number
        error?: string
      }
    },
    enabled: false, // Only run when explicitly called
  })
}
