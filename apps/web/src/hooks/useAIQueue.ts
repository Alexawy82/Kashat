import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

// ==================== TYPES ====================

export interface AIQueueStats {
  active: number
  pending: number
  completed: number
  failed: number
  paused: number
  cancelled: number
  is_paused: boolean
  batch_size: number
  batch_delay_ms: number
  auto_start_on_import: boolean
}

export interface AIBulkJob {
  job_id: string
  job_type: string
  total_transactions: number
  processed_transactions: number
  enhanced_transactions: number
  status: 'processing' | 'completed' | 'failed' | 'paused' | 'cancelled' | 'pending'
  created_at: string
  completed_at: string | null
  progress_percentage: number
  error_message?: string
}

export interface AIQueueSettings {
  ai_batch_size: number
  ai_batch_delay_ms: number
  ai_auto_start_on_import: boolean
  ai_max_concurrent_jobs: number
  ai_job_timeout_minutes: number
  ai_processing_paused: boolean
}

// ==================== QUEUE STATS ====================

export function useAIQueueStats() {
  return useQuery({
    queryKey: ['ai-queue-stats'],
    queryFn: async () => {
      const { data, error } = await client.get<AIQueueStats>('/api/ai/queue/stats')
      if (error) throw new Error('Failed to fetch queue stats')
      return data
    },
    refetchInterval: 3000, // Poll every 3 seconds
  })
}

// ==================== BULK JOBS ====================

export function useAIBulkJobs(limit = 20) {
  return useQuery({
    queryKey: ['ai-bulk-jobs', limit],
    queryFn: async () => {
      const { data, error } = await client.get<{ jobs: AIBulkJob[] }>('/api/ai/bulk-jobs', {
        params: { query: { limit } }
      })
      if (error) throw new Error('Failed to fetch bulk jobs')
      return data?.jobs || []
    },
    refetchInterval: 5000, // Poll every 5 seconds
  })
}

export function useAIJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['ai-job', jobId],
    queryFn: async () => {
      if (!jobId) return null
      const { data, error } = await client.get<AIBulkJob>(`/api/ai/bulk-job/${jobId}`)
      if (error) throw new Error('Failed to fetch job status')
      return data
    },
    enabled: !!jobId,
    refetchInterval: 2000, // Poll every 2 seconds when active
  })
}

// ==================== QUEUE CONTROL ====================

export function usePauseAIProcessing() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post<{ paused: boolean; jobs_paused: number; message: string }>(
        '/api/ai/queue/pause'
      )
      if (error) throw new Error('Failed to pause AI processing')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-queue-stats'] })
      queryClient.invalidateQueries({ queryKey: ['ai-bulk-jobs'] })
    }
  })
}

export function useResumeAIProcessing() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post<{ resumed: boolean; message: string }>(
        '/api/ai/queue/resume'
      )
      if (error) throw new Error('Failed to resume AI processing')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-queue-stats'] })
      queryClient.invalidateQueries({ queryKey: ['ai-bulk-jobs'] })
    }
  })
}

export function useCancelAIJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobId: string) => {
      const { data, error } = await client.post<{ job_id: string; status: string }>(
        `/api/ai/bulk-job/${jobId}/cancel`
      )
      if (error) throw new Error('Failed to cancel job')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-bulk-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['ai-queue-stats'] })
    }
  })
}

export function useRetryAIJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobId: string) => {
      const { data, error } = await client.post<{ job_id: string; status: string; transaction_count: number }>(
        `/api/ai/bulk-job/${jobId}/retry`
      )
      if (error) throw new Error('Failed to retry job')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-bulk-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['ai-queue-stats'] })
    }
  })
}

// ==================== QUEUE SETTINGS ====================

export function useUpdateQueueSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (settings: Partial<{
      batch_size: number
      batch_delay_ms: number
      auto_start_on_import: boolean
      max_concurrent_jobs: number
      job_timeout_minutes: number
    }>) => {
      const { data, error } = await client.post<{ updated: boolean; changes: object; current_settings: AIQueueSettings }>(
        '/api/ai/queue/settings',
        { body: settings }
      )
      if (error) throw new Error('Failed to update queue settings')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-queue-stats'] })
      queryClient.invalidateQueries({ queryKey: ['app-settings'] })
    }
  })
}
