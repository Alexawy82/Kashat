'use client'

import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useConfirm } from '@/components/ui/ConfirmDialog'
import {
  Upload, FileText, FileSpreadsheet, Trash2, RefreshCw,
  CheckCircle, XCircle, Clock, Loader2, FolderOpen, AlertTriangle
} from 'lucide-react'
import { useImportRuns, useBulkUpload, useDeleteImportRun, useReprocessImportRun } from '@/hooks/useImports'
import { PageHeader } from '@/components/ui/page-header'

const statusConfig = {
  empty: { icon: Clock, color: 'text-gray-500', bg: 'bg-gray-100', label: 'Empty' },
  ready: { icon: CheckCircle, color: 'text-blue-500', bg: 'bg-blue-100', label: 'Ready' },
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', label: 'Completed' },
  processing: { icon: Loader2, color: 'text-yellow-500', bg: 'bg-yellow-100', label: 'Processing' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', label: 'Failed' },
}

export default function ImportPage() {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const { confirm, ConfirmDialog } = useConfirm()

  const { data: runsData, isLoading: runsLoading, refetch: refetchRuns } = useImportRuns()
  const bulkUpload = useBulkUpload()
  const deleteRun = useDeleteImportRun()
  const reprocessRun = useReprocessImportRun()

  const runs = runsData || []

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.name.endsWith('.csv') || file.name.endsWith('.pdf')
    )
    if (files.length > 0) {
      setSelectedFiles(prev => [...prev, ...files])
      setUploadError(null)
    } else {
      setUploadError('Only CSV and PDF files are supported')
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      setSelectedFiles(prev => [...prev, ...files])
      setUploadError(null)
    }
  }, [])

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    try {
      setUploadError(null)
      await bulkUpload.mutateAsync({
        files: selectedFiles,
        enable_ai: true,
        enable_workflow: true
      })
      setSelectedFiles([])
      refetchRuns()
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
    }
  }

  const handleDelete = async (runId: string) => {
    const confirmed = await confirm({
      title: 'Delete Import Run',
      description: 'Are you sure you want to delete this import run? This will also delete all imported transactions.',
      confirmLabel: 'Delete',
      variant: 'destructive',
    })
    if (!confirmed) return
    try {
      await deleteRun.mutateAsync(runId)
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const handleReprocess = async (runId: string) => {
    try {
      await reprocessRun.mutateAsync({ runId, enable_workflow: true })
    } catch (error) {
      console.error('Reprocess failed:', error)
    }
  }

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Import Data"
        description="Upload bank statements (CSV or PDF) to import transactions."
        helpItems={[
          "Drag and drop CSV or PDF bank statements to upload",
          "PDF statements are parsed using AI vision for accuracy",
          "Duplicate transactions are automatically detected and skipped",
          "After import, transactions are auto-categorized using AI",
          "Use 'Reprocess' to re-run categorization on existing imports"
        ]}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Area */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload Files
            </CardTitle>
            <CardDescription>
              Drag and drop files or click to browse. Supports CSV and PDF bank statements.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center transition-colors
                ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
                ${selectedFiles.length > 0 ? 'border-green-500 bg-green-50' : ''}
              `}
            >
              <input
                type="file"
                accept=".csv,.pdf"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <FolderOpen className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-sm font-medium">
                  {dragActive ? 'Drop files here...' : 'Drop files here or click to browse'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  CSV, PDF (max 50MB each)
                </p>
              </label>
            </div>

            {/* Selected Files */}
            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Selected Files ({selectedFiles.length})</p>
                {selectedFiles.map((file, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-muted rounded-md">
                    <div className="flex items-center gap-2">
                      {file.name.endsWith('.csv') ? (
                        <FileSpreadsheet className="h-4 w-4 text-green-600" />
                      ) : (
                        <FileText className="h-4 w-4 text-red-600" />
                      )}
                      <span className="text-sm truncate max-w-[200px]">{file.name}</span>
                      <span className="text-xs text-muted-foreground">
                        ({(file.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => removeFile(i)}>
                      <XCircle className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {uploadError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{uploadError}</AlertDescription>
              </Alert>
            )}

            <Button
              onClick={handleUpload}
              disabled={selectedFiles.length === 0 || bulkUpload.isPending}
              className="w-full"
            >
              {bulkUpload.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''}
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Import History */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Import History</CardTitle>
                <CardDescription>Recent import runs</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetchRuns()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : runs.length === 0 ? (
              <div className="text-center p-8 text-muted-foreground">
                <FolderOpen className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No imports yet</p>
                <p className="text-xs">Upload files to get started</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {runs.map((run: any) => {
                  const status = run.status || 'ready'
                  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.ready
                  const Icon = config.icon
                  const isProcessing = status === 'processing'

                  return (
                    <div key={run.run_id} className="p-3 border rounded-lg">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`p-1.5 rounded ${config.bg}`}>
                            <Icon className={`h-4 w-4 ${config.color} ${isProcessing ? 'animate-spin' : ''}`} />
                          </div>
                          <div>
                            <p className="text-sm font-medium">
                              {run.file_count || 0} file{run.file_count !== 1 ? 's' : ''}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(run.started_at).toLocaleDateString()} {new Date(run.started_at).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                        <Badge variant="outline" className={config.color}>
                          {config.label}
                        </Badge>
                      </div>

                      <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{run.tx_count || 0} transactions</span>
                        {run.min_date && run.max_date && (
                          <span>
                            {new Date(run.min_date).toLocaleDateString()} - {new Date(run.max_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      <div className="mt-3 flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReprocess(run.run_id)}
                          disabled={reprocessRun.isPending}
                        >
                          <RefreshCw className="h-3 w-3 mr-1" />
                          Reprocess
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(run.run_id)}
                          disabled={deleteRun.isPending}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <ConfirmDialog />
    </div>
  )
}
