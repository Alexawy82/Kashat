import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

async function _runPostImportP2PDetection() {
  // Best-effort: P2P fields are used by the Transfers UI; run after import so it shows up immediately.
  try {
    await client.post('/api/detect/p2p', { params: { query: { commit: true } } })
  } catch {
    // ignore
  }
}

// List import runs
export function useImportRuns(limit: number = 20) {
  return useQuery({
    queryKey: ['import-runs', limit],
    queryFn: async () => {
      const { data, error } = await client.get('/api/imports/runs', {
        params: { query: { limit } }
      })
      if (error) throw new Error('Failed to fetch import runs')
      return data as any
    },
  })
}

// Get files in a run
export function useImportRunFiles(runId: string) {
  return useQuery({
    queryKey: ['import-run-files', runId],
    queryFn: async () => {
      const { data, error } = await client.get('/api/imports/runs/{run_id}/files', {
        params: { path: { run_id: runId } }
      })
      if (error) throw new Error('Failed to fetch run files')
      return data as any
    },
    enabled: !!runId,
  })
}

// Get run summary
export function useImportRunSummary(runId: string) {
  return useQuery({
    queryKey: ['import-run-summary', runId],
    queryFn: async () => {
      const { data, error } = await client.get('/api/imports/runs/{run_id}/summary', {
        params: { path: { run_id: runId } }
      })
      if (error) throw new Error('Failed to fetch run summary')
      return data as any
    },
    enabled: !!runId,
  })
}

// Upload CSV
export function useUploadCSV() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      file: File
      account_id?: string
      run_id?: string
      enable_workflow?: boolean
    }) => {
      const formData = new FormData()
      formData.append('file', params.file)

      const queryParams = new URLSearchParams()
      if (params.account_id) queryParams.set('account_id', params.account_id)
      if (params.run_id) queryParams.set('run_id', params.run_id)
      if (params.enable_workflow) queryParams.set('enable_workflow', 'true')

      const url = `/api/imports/csv${queryParams.toString() ? '?' + queryParams.toString() : ''}`

      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to upload CSV')
      }

      return response.json()
    },
    onSuccess: () => {
      _runPostImportP2PDetection()
      queryClient.invalidateQueries({ queryKey: ['import-runs'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
    }
  })
}

// Upload PDF
export function useUploadPDF() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      file: File
      account_id?: string
      run_id?: string
    }) => {
      const formData = new FormData()
      formData.append('file', params.file)

      const queryParams = new URLSearchParams()
      if (params.account_id) queryParams.set('account_id', params.account_id)
      if (params.run_id) queryParams.set('run_id', params.run_id)

      const url = `/api/imports/pdf${queryParams.toString() ? '?' + queryParams.toString() : ''}`

      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to upload PDF')
      }

      return response.json()
    },
    onSuccess: () => {
      _runPostImportP2PDetection()
      queryClient.invalidateQueries({ queryKey: ['import-runs'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
    }
  })
}

// Bulk upload - uses direct backend call to avoid Next.js proxy timeout
export function useBulkUpload() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      files: File[]
      account_id?: string
      enable_ai?: boolean
      enable_workflow?: boolean
    }) => {
      const formData = new FormData()
      params.files.forEach(file => {
        formData.append('files', file)
      })

      const queryParams = new URLSearchParams()
      if (params.account_id) queryParams.set('account_id', params.account_id)
      if (params.enable_ai !== undefined) queryParams.set('enable_ai', String(params.enable_ai))
      if (params.enable_workflow !== undefined) queryParams.set('enable_workflow', String(params.enable_workflow))

      // For bulk uploads, we bypass the Next.js proxy which has a ~2min timeout.
      // Use the backend origin directly for long-running uploads.
      const backendOrigin = typeof window !== 'undefined'
        ? (process.env.NEXT_PUBLIC_API_BASE?.startsWith('http')
            ? new URL(process.env.NEXT_PUBLIC_API_BASE).origin
            : window.location.origin)
        : ''

      // Try direct backend first, fall back to proxy
      const directUrl = `${backendOrigin}/api/imports/bulk${queryParams.toString() ? '?' + queryParams.toString() : ''}`
      const proxyUrl = `/api/imports/bulk${queryParams.toString() ? '?' + queryParams.toString() : ''}`

      // Use AbortController for timeout handling (10 minute timeout for bulk)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000)

      try {
        const response = await fetch(directUrl, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        })
        clearTimeout(timeoutId)

        if (!response.ok) {
          const error = await response.json().catch(() => ({}))
          throw new Error(error.detail || 'Failed to bulk upload')
        }

        return response.json()
      } catch (err: any) {
        clearTimeout(timeoutId)
        // If direct call fails (e.g., CORS), try proxy as fallback
        if (err.name === 'AbortError') {
          throw new Error('Upload timed out after 10 minutes')
        }
        // Fallback to proxy for local dev where CORS might not be configured
        const response = await fetch(proxyUrl, {
          method: 'POST',
          body: formData,
        })
        if (!response.ok) {
          const error = await response.json().catch(() => ({}))
          throw new Error(error.detail || 'Failed to bulk upload')
        }
        return response.json()
      }
    },
    onSuccess: () => {
      _runPostImportP2PDetection()
      queryClient.invalidateQueries({ queryKey: ['import-runs'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
    }
  })
}

// Delete import run
export function useDeleteImportRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string) => {
      const { data, error } = await client.delete('/api/imports/runs/{run_id}', {
        params: { path: { run_id: runId } }
      })
      if (error) throw new Error('Failed to delete import run')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['import-runs'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    }
  })
}

// Reprocess import run
export function useReprocessImportRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (params: {
      runId: string
      account_id?: string
      enable_workflow?: boolean
    }) => {
      const { data, error } = await client.post('/api/imports/runs/{run_id}/reprocess', {
        params: {
          path: { run_id: params.runId },
          query: {
            account_id: params.account_id,
            enable_workflow: params.enable_workflow
          }
        }
      })
      if (error) throw new Error('Failed to reprocess import run')
      return data
    },
    onSuccess: () => {
      _runPostImportP2PDetection()
      queryClient.invalidateQueries({ queryKey: ['import-runs'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['p2p-summary'] })
    }
  })
}

// Get bulk job status
export function useBulkJobStatus(jobId: string) {
  return useQuery({
    queryKey: ['bulk-job', jobId],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/bulk-job/{job_id}', {
        params: { path: { job_id: jobId } }
      })
      if (error) throw new Error('Failed to fetch job status')
      return data as any
    },
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Poll every 2 seconds while job is running
      const status = data?.state?.data?.status
      return status === 'running' || status === 'pending' ? 2000 : false
    }
  })
}
