"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Terminal, Loader2, Database, Cpu, HardDrive, Server, RefreshCw, CheckCircle, XCircle, AlertTriangle, Clock, Activity } from "lucide-react"
import { useState, useEffect } from "react"
import { useHealthDetailed, useAIStatus } from "@/hooks/usePulse"
import { useImportRuns } from "@/hooks/useImports"
import { useDataStats } from "@/hooks/useSettings"

// Log entry type for the console
interface LogEntry {
  timestamp: Date
  type: 'system' | 'ai' | 'db' | 'import' | 'warn' | 'error'
  message: string
}

export default function SystemSettingsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useHealthDetailed()
  const { data: aiStatus, isLoading: aiLoading } = useAIStatus()
  const { data: importRuns } = useImportRuns()
  const { data: dataStats } = useDataStats()

  // Generate log entries from real data
  useEffect(() => {
    const newLogs: LogEntry[] = []
    const now = new Date()

    // System status
    if (health) {
      newLogs.push({
        timestamp: now,
        type: 'system',
        message: `LedgerLoop ${health.version} - Status: ${health.status.toUpperCase()}`
      })
      newLogs.push({
        timestamp: now,
        type: 'system',
        message: `Uptime: ${health.uptime?.human || 'unknown'}`
      })
    }

    // Database status
    if (health?.components?.database) {
      const db = health.components.database
      if (db.status === 'healthy') {
        newLogs.push({
          timestamp: now,
          type: 'db',
          message: `DuckDB connected - ${db.transaction_count?.toLocaleString() || 0} transactions, ${db.table_count || 0} tables`
        })
      } else {
        newLogs.push({
          timestamp: now,
          type: 'error',
          message: `Database ${db.status}: ${db.error || 'unknown error'}`
        })
      }
    }

    // Filesystem status
    if (health?.components?.filesystem) {
      const fs = health.components.filesystem
      if (fs.free_space_gb !== undefined) {
        newLogs.push({
          timestamp: now,
          type: 'system',
          message: `Disk: ${fs.free_space_gb?.toFixed(1)}GB free (${fs.disk_usage_percent?.toFixed(1)}% used)`
        })
      }
    }

    // AI status
    if (aiStatus) {
      if (aiStatus.ok) {
        newLogs.push({
          timestamp: now,
          type: 'ai',
          message: `AI Provider: ${aiStatus.provider || 'configured'} (${aiStatus.latency_ms || 0}ms latency)`
        })
      } else {
        newLogs.push({
          timestamp: now,
          type: 'warn',
          message: `AI Service: ${aiStatus.error || 'not configured'}`
        })
      }
    }

    // Data stats
    if (dataStats) {
      newLogs.push({
        timestamp: now,
        type: 'db',
        message: `Stats: ${dataStats.transactions || 0} txns, ${dataStats.categories || 0} categories, ${dataStats.rules || 0} rules`
      })
    }

    // Recent imports
    if (importRuns && importRuns.length > 0) {
      const recent = importRuns[0]
      newLogs.push({
        timestamp: now,
        type: 'import',
        message: `Last import: ${recent.status} - ${recent.file_count || 0} files, ${recent.tx_count || 0} transactions`
      })
    }

    setLogs(newLogs)
  }, [health, aiStatus, dataStats, importRuns])

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'text-green-500'
      case 'degraded':
        return 'text-yellow-500'
      case 'unhealthy':
        return 'text-red-500'
      default:
        return 'text-gray-500'
    }
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'degraded':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getLogColor = (type: string) => {
    switch (type) {
      case 'system':
        return 'text-blue-400'
      case 'ai':
        return 'text-purple-400'
      case 'db':
        return 'text-green-400'
      case 'import':
        return 'text-cyan-400'
      case 'warn':
        return 'text-yellow-400'
      case 'error':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Real-time system monitoring and diagnostics.
        </p>
        <Button variant="outline" size="sm" onClick={() => refetchHealth()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Status Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Overall Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Status</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {healthLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Loading...</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {getStatusIcon(health?.status)}
                <span className={`text-2xl font-bold capitalize ${getStatusColor(health?.status)}`}>
                  {health?.status || 'Unknown'}
                </span>
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              v{health?.version || '...'}
            </p>
          </CardContent>
        </Card>

        {/* Database Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Database</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {getStatusIcon(health?.components?.database?.status)}
              <span className={`text-2xl font-bold capitalize ${getStatusColor(health?.components?.database?.status)}`}>
                {health?.components?.database?.status || 'Unknown'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {(dataStats?.transactions || 0).toLocaleString()} transactions
            </p>
          </CardContent>
        </Card>

        {/* AI Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Service</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {aiLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Checking...</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {getStatusIcon(aiStatus?.ok ? 'healthy' : 'degraded')}
                <span className={`text-2xl font-bold ${aiStatus?.ok ? 'text-green-500' : 'text-yellow-500'}`}>
                  {aiStatus?.ok ? 'Online' : 'Offline'}
                </span>
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {aiStatus?.provider || 'Not configured'}
              {aiStatus?.latency_ms ? ` - ${aiStatus.latency_ms}ms` : ''}
            </p>
          </CardContent>
        </Card>

        {/* Disk Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {getStatusIcon(health?.components?.filesystem?.status)}
              <span className={`text-2xl font-bold ${getStatusColor(health?.components?.filesystem?.status)}`}>
                {health?.components?.filesystem?.free_space_gb?.toFixed(1) || '--'} GB
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {health?.components?.filesystem?.disk_usage_percent?.toFixed(1) || '--'}% used
            </p>
            <div className="mt-2 h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${(health?.components?.filesystem?.disk_usage_percent || 0) > 90 ? 'bg-red-500' : (health?.components?.filesystem?.disk_usage_percent || 0) > 75 ? 'bg-yellow-500' : 'bg-green-500'}`}
                style={{ width: `${health?.components?.filesystem?.disk_usage_percent || 0}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Quick Stats */}
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Data Overview
            </CardTitle>
            <CardDescription>Current database statistics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Transactions</span>
                <Badge variant="secondary">{(dataStats?.transactions || 0).toLocaleString()}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Categories</span>
                <Badge variant="secondary">{dataStats?.categories || 0}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Rules</span>
                <Badge variant="secondary">{dataStats?.rules || 0}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Import Runs</span>
                <Badge variant="secondary">{dataStats?.import_runs || 0}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">AI Jobs</span>
                <Badge variant="secondary">{dataStats?.ai_jobs || 0}</Badge>
              </div>
              <div className="flex justify-between items-center border-t pt-2 mt-2">
                <span className="text-sm font-medium">DB Size</span>
                <Badge variant="outline">
                  {dataStats?.db_size_bytes
                    ? `${(dataStats.db_size_bytes / (1024 * 1024)).toFixed(1)} MB`
                    : '--'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Real-time Console */}
        <Card className="col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>System Log</CardTitle>
              <CardDescription>Live status updates</CardDescription>
            </div>
            <Terminal className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs h-[220px] overflow-y-auto space-y-1">
              {logs.length === 0 ? (
                <div className="text-gray-500 flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Initializing system monitors...
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className={getLogColor(log.type)}>
                    [{log.type.toUpperCase()}] {log.message}
                  </div>
                ))
              )}
              <div className="text-green-400 animate-pulse mt-2">_</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Imports */}
      {importRuns && importRuns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Import Activity</CardTitle>
            <CardDescription>Last 5 import runs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {importRuns.slice(0, 5).map((run: any, i: number) => (
                <div key={run.id || i} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                  <div className="flex items-center gap-3">
                    <Badge variant={run.status === 'completed' ? 'default' : run.status === 'failed' ? 'destructive' : 'secondary'}>
                      {run.status}
                    </Badge>
                    <span className="text-sm">{run.file_count || 0} files</span>
                    <span className="text-sm text-muted-foreground">-</span>
                    <span className="text-sm">{run.tx_count || 0} transactions</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {run.created_at ? new Date(run.created_at).toLocaleString() : 'Unknown'}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
