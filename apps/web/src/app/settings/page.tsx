"use client"

import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import {
  Trash2, Download, Database, HardDrive, RefreshCw, AlertTriangle,
  Loader2, CheckCircle, Brain, Settings2, Sparkles, FileDown, Save, Zap, LayoutDashboard,
  Pause, Play, X, RotateCcw, Activity, PiggyBank, DollarSign
} from "lucide-react"
import {
  useDataStats,
  useMerchantMemory,
  useDeleteMerchantMemory,
  useCreateBackup,
  useOptimizeDatabase,
  useResetAI,
  useFactoryReset,
  useExportCSV,
  useAppSettings,
  useSaveSettings,
  useAISettings,
  useSaveAISettings,
  AppSettings
} from "@/hooks/useSettings"
import { useAIStatus, useAIPing } from "@/hooks/usePulse"
import { useAISuccessMetrics, useCategorizeAllTransactions, useCategorizationStatus } from "@/hooks/useCategories"
import {
  useAIAccuracy,
  useAIWorkflowStats,
  useBackfillMemory,
  useCleanupIntelligenceCache,
  useIntelligenceCacheStats,
  useMergeRecurringDuplicates,
  useReclassifyRecurring,
  useReclassifyWithLLM,
} from "@/hooks/useRecurring"
import {
  useAIQueueStats,
  useAIBulkJobs,
  usePauseAIProcessing,
  useResumeAIProcessing,
  useCancelAIJob,
  useRetryAIJob,
  useUpdateQueueSettings
} from "@/hooks/useAIQueue"
import { Progress } from "@/components/ui/progress"
import { PageHeader } from '@/components/ui/page-header'
import { useConfirm } from "@/components/ui/ConfirmDialog"
import { toast } from "@/components/ui/Toaster"
import {
  useBudgetSettings,
  useUpdateBudgetSettings,
  useDetectIncome,
  useIncome,
} from "@/hooks/useBudgetIntelligence"

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function BudgetSettingsTab() {
  const { data: budgetSettings, isLoading: budgetSettingsLoading } = useBudgetSettings()
  const updateBudgetSettings = useUpdateBudgetSettings()
  const { data: income, isLoading: incomeLoading } = useIncome()
  const detectIncome = useDetectIncome()

  const [localBudgetSettings, setLocalBudgetSettings] = useState({
    include_irregular_income: false,
    pace_warning_threshold: 0.8,
    savings_goal_percent: 0.20,
    auto_suggest_enabled: true,
    suggestion_frequency: 'monthly' as 'weekly' | 'monthly' | 'on_demand',
  })

  useEffect(() => {
    if (budgetSettings) {
      setLocalBudgetSettings({
        include_irregular_income: budgetSettings.include_irregular_income ?? false,
        pace_warning_threshold: budgetSettings.pace_warning_threshold ?? 0.8,
        savings_goal_percent: budgetSettings.savings_goal_percent ?? 0.20,
        auto_suggest_enabled: budgetSettings.auto_suggest_enabled ?? true,
        suggestion_frequency: budgetSettings.suggestion_frequency ?? 'monthly',
      })
    }
  }, [budgetSettings])

  const handleSaveBudgetSettings = (updates: Partial<typeof localBudgetSettings>) => {
    const newSettings = { ...localBudgetSettings, ...updates }
    setLocalBudgetSettings(newSettings)
    updateBudgetSettings.mutate(newSettings)
  }

  const totalMonthlyIncome = income?.reduce((sum, src) => {
    if (!src.is_active) return sum
    switch (src.frequency) {
      case 'weekly': return sum + src.avg_amount * 4.33
      case 'biweekly': return sum + src.avg_amount * 2.17
      case 'monthly': return sum + src.avg_amount
      case 'irregular': return sum + src.avg_amount * 0.5
      default: return sum + src.avg_amount
    }
  }, 0) || 0

  if (budgetSettingsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Budget Intelligence Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PiggyBank className="h-5 w-5" />
            Budget Intelligence
          </CardTitle>
          <CardDescription>Configure smart budget suggestions and pace tracking</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Default Savings Goal ({(localBudgetSettings.savings_goal_percent * 100).toFixed(0)}%)</Label>
            <Slider
              value={[localBudgetSettings.savings_goal_percent * 100]}
              onValueChange={([v]) => handleSaveBudgetSettings({ savings_goal_percent: v / 100 })}
              min={5}
              max={50}
              step={5}
            />
            <p className="text-xs text-muted-foreground">
              Target percentage of income to save when generating smart budgets
            </p>
          </div>

          <div className="space-y-2">
            <Label>Pace Warning Threshold ({(localBudgetSettings.pace_warning_threshold * 100).toFixed(0)}%)</Label>
            <Slider
              value={[localBudgetSettings.pace_warning_threshold * 100]}
              onValueChange={([v]) => handleSaveBudgetSettings({ pace_warning_threshold: v / 100 })}
              min={50}
              max={95}
              step={5}
            />
            <p className="text-xs text-muted-foreground">
              Show warnings when spending pace exceeds this percentage of time elapsed
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Include Irregular Income</Label>
              <p className="text-xs text-muted-foreground">
                Factor in irregular income sources when calculating budgets
              </p>
            </div>
            <Switch
              checked={localBudgetSettings.include_irregular_income}
              onCheckedChange={(v) => handleSaveBudgetSettings({ include_irregular_income: v })}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Auto-Suggest Budgets</Label>
              <p className="text-xs text-muted-foreground">
                Automatically generate budget suggestions based on spending patterns
              </p>
            </div>
            <Switch
              checked={localBudgetSettings.auto_suggest_enabled}
              onCheckedChange={(v) => handleSaveBudgetSettings({ auto_suggest_enabled: v })}
            />
          </div>

          <div className="space-y-2">
            <Label>Suggestion Frequency</Label>
            <Select
              value={localBudgetSettings.suggestion_frequency}
              onValueChange={(v: 'weekly' | 'monthly' | 'on_demand') =>
                handleSaveBudgetSettings({ suggestion_frequency: v })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="on_demand">On Demand Only</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              How often to refresh budget suggestions
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Income Sources */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Detected Income
          </CardTitle>
          <CardDescription>
            Income sources detected from your transactions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {incomeLoading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : income && income.length > 0 ? (
            <>
              <div className="space-y-2">
                {income.filter(s => s.is_active).map((source) => (
                  <div
                    key={source.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div>
                      <div className="font-medium text-sm">{source.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {source.frequency} &bull; {(source.confidence * 100).toFixed(0)}% confidence
                      </div>
                    </div>
                    <div className="text-green-600 font-medium">
                      +${source.avg_amount.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-green-800 font-medium">Est. Monthly Income</span>
                  <span className="text-lg font-bold text-green-600">
                    ${totalMonthlyIncome.toFixed(2)}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-8">
              <DollarSign className="h-12 w-12 text-muted-foreground mx-auto mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">No income sources detected yet.</p>
              <p className="text-xs text-muted-foreground">
                Click below to analyze your transactions for income patterns.
              </p>
            </div>
          )}

          <Button
            variant="outline"
            className="w-full"
            onClick={() => detectIncome.mutate()}
            disabled={detectIncome.isPending}
          >
            {detectIncome.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {income && income.length > 0 ? 'Re-detect Income' : 'Detect Income'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default function SettingsPage() {
  const [confirmReset, setConfirmReset] = useState('')
  const [localSettings, setLocalSettings] = useState<Partial<AppSettings>>({})
  const [openAiKeyInput, setOpenAiKeyInput] = useState('')
  const [openAiKeySet, setOpenAiKeySet] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  const { data: settings, isLoading: settingsLoading } = useAppSettings()
  const { data: aiSettings, isLoading: aiSettingsLoading } = useAISettings()
  const { data: stats, isLoading: statsLoading } = useDataStats()
  const { data: merchantMemory, isLoading: memoryLoading } = useMerchantMemory()
  const { data: aiStatus, isLoading: aiStatusLoading, refetch: refetchAIStatus } = useAIStatus()
  const { data: aiMetrics } = useAISuccessMetrics()
  const { data: recurringAiStats, isLoading: recurringStatsLoading } = useAIWorkflowStats()
  const { data: recurringAccuracy } = useAIAccuracy()
  const { data: intelligenceCacheStats } = useIntelligenceCacheStats()
  const reclassifyRecurring = useReclassifyRecurring()
  const mergeDuplicates = useMergeRecurringDuplicates()
  const reclassifyWithLLM = useReclassifyWithLLM()
  const backfillMemory = useBackfillMemory()
  const cleanupCache = useCleanupIntelligenceCache()
  const aiPing = useAIPing()

  const saveSettings = useSaveSettings()
  const saveAISettings = useSaveAISettings()
  const deleteMerchantMemory = useDeleteMerchantMemory()
  const createBackup = useCreateBackup()
  const optimizeDb = useOptimizeDatabase()
  const resetAI = useResetAI()
  const factoryReset = useFactoryReset()
  const exportCSV = useExportCSV()

  // AI Queue hooks
  const { data: queueStats, isLoading: queueStatsLoading } = useAIQueueStats()
  const { data: bulkJobs } = useAIBulkJobs(10)
  const pauseAI = usePauseAIProcessing()
  const resumeAI = useResumeAIProcessing()
  const cancelJob = useCancelAIJob()
  const retryJob = useRetryAIJob()
  const updateQueueSettings = useUpdateQueueSettings()
  const { confirm, ConfirmDialog } = useConfirm()

  // New categorization hooks (race-condition safe)
  const categorizeAll = useCategorizeAllTransactions()
  const { data: categorizationStatus } = useCategorizationStatus()
  const isCategorizationRunning = categorizationStatus?.current_job?.status === 'processing'

  // Initialize local settings from fetched settings
  useEffect(() => {
    if (settings) {
      setLocalSettings(settings)
      setOpenAiKeySet(Boolean(settings.ai_openai_api_key_set))
    }
  }, [settings])

  const updateSetting = (key: keyof AppSettings, value: any) => {
    setLocalSettings(prev => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  const handleSaveSettings = () => {
    const payload: Partial<AppSettings> = { ...localSettings }
    delete (payload as any).ai_openai_api_key_set
    if (openAiKeyInput.trim()) {
      payload.ai_openai_api_key = openAiKeyInput.trim()
    } else {
      delete (payload as any).ai_openai_api_key
    }
    saveSettings.mutate(payload, {
      onSuccess: () => {
        setHasChanges(false)
        if (openAiKeyInput.trim()) {
          setOpenAiKeyInput('')
          setOpenAiKeySet(true)
        }
      }
    })
  }

  const handleClearOpenAiKey = () => {
    saveSettings.mutate({ ai_openai_api_key: '' }, {
      onSuccess: () => {
        setOpenAiKeyInput('')
        setOpenAiKeySet(false)
      }
    })
  }

  const handleSaveAISettings = (updates: Parameters<typeof saveAISettings.mutate>[0]) => {
    saveAISettings.mutate(updates)
  }

  const handleDeleteMemory = async (pattern: string) => {
    const confirmed = await confirm({
      title: 'Remove Mapping',
      description: `Remove learned mapping for "${pattern}"?`,
      confirmLabel: 'Remove',
      variant: 'destructive',
    })
    if (confirmed) {
      deleteMerchantMemory.mutate(pattern)
    }
  }

  const handleBackup = () => {
    createBackup.mutate(undefined, {
      onSuccess: (data) => {
        toast.success(`Backup created: ${data?.backup_file}`)
      }
    })
  }

  const handleOptimize = () => {
    optimizeDb.mutate(undefined, {
      onSuccess: () => {
        toast.success('Database optimized successfully!')
      }
    })
  }

  const handleResetAI = async () => {
    const confirmed = await confirm({
      title: 'Reset AI Fields',
      description: 'Reset all AI fields on transactions? This will clear AI-generated merchant names and category suggestions.',
      confirmLabel: 'Reset',
      variant: 'destructive',
    })
    if (confirmed) {
      resetAI.mutate()
    }
  }

  const handleFactoryReset = () => {
    if (confirmReset !== 'FACTORY RESET') {
      toast.error('Type "FACTORY RESET" to confirm')
      return
    }
    factoryReset.mutate(undefined, {
      onSuccess: () => {
        setConfirmReset('')
        toast.success('Factory reset complete. Database has been wiped.')
      }
    })
  }

  const handleExport = () => {
    exportCSV.mutate({})
  }

  if (settingsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Configure your Kashat experience"
        helpItems={[
          "General: Transaction defaults, recurring detection, and display preferences",
          "AI & Intelligence: Configure AI provider, auto-categorization, and merchant memory",
          "Budget: Set savings goals, pace warnings, and income detection settings",
          "Dashboard: Customize time periods and enable/disable features",
          "Data Management: Export, backup, optimize, or reset your database"
        ]}
      />

      {/* Save button for pending changes */}
      {hasChanges && (
        <div className="flex justify-end">
          <Button onClick={handleSaveSettings} disabled={saveSettings.isPending}>
            {saveSettings.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Changes
          </Button>
        </div>
      )}

      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="ai">AI & Intelligence</TabsTrigger>
          <TabsTrigger value="budget">Budget</TabsTrigger>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="data">Data Management</TabsTrigger>
        </TabsList>

        {/* GENERAL TAB */}
        <TabsContent value="general">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Transaction Defaults */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5" />
                  Transaction Defaults
                </CardTitle>
                <CardDescription>Default settings for transaction views</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Default Sort By</Label>
                    <Select
                      value={localSettings.tx_default_sort_by || 'posted_at'}
                      onValueChange={(v) => updateSetting('tx_default_sort_by', v)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="posted_at">Date</SelectItem>
                        <SelectItem value="amount">Amount</SelectItem>
                        <SelectItem value="description">Description</SelectItem>
                        <SelectItem value="category">Category</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Sort Direction</Label>
                    <Select
                      value={localSettings.tx_default_sort_dir || 'desc'}
                      onValueChange={(v) => updateSetting('tx_default_sort_dir', v)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="desc">Newest First</SelectItem>
                        <SelectItem value="asc">Oldest First</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Include Transfers</Label>
                    <p className="text-xs text-muted-foreground">Show internal transfers by default</p>
                  </div>
                  <Switch
                    checked={localSettings.tx_include_transfers_default ?? false}
                    onCheckedChange={(v) => updateSetting('tx_include_transfers_default', v)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Business Filter</Label>
                  <Select
                    value={localSettings.tx_business_filter_default || 'all'}
                    onValueChange={(v) => updateSetting('tx_business_filter_default', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Transactions</SelectItem>
                      <SelectItem value="business">Business Only</SelectItem>
                      <SelectItem value="personal">Personal Only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Recurring Detection */}
            <Card>
              <CardHeader>
                <CardTitle>Recurring Detection</CardTitle>
                <CardDescription>Settings for subscription detection</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Amount Tolerance ({((localSettings.recurring_tolerance || 0.10) * 100).toFixed(0)}%)</Label>
                  <Slider
                    value={[(localSettings.recurring_tolerance || 0.10) * 100]}
                    onValueChange={([v]) => updateSetting('recurring_tolerance', v / 100)}
                    min={1}
                    max={20}
                    step={1}
                  />
                  <p className="text-xs text-muted-foreground">
                    How much subscription amounts can vary and still be considered the same
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Recurring Display */}
            <Card>
              <CardHeader>
                <CardTitle>Recurring Display</CardTitle>
                <CardDescription>Customize how recurring data is presented</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Default View</Label>
                  <Select
                    value={localSettings.recurring_default_view || 'all'}
                    onValueChange={(v) => updateSetting('recurring_default_view', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="by-type">By Type</SelectItem>
                      <SelectItem value="by-due-date">By Due Date</SelectItem>
                      <SelectItem value="essential-first">Essential First</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Sparkline Period</Label>
                  <Select
                    value={String(localSettings.recurring_sparkline_period || 12)}
                    onValueChange={(v) => updateSetting('recurring_sparkline_period', parseInt(v, 10))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="6">Last 6 months</SelectItem>
                      <SelectItem value="12">Last 12 months</SelectItem>
                      <SelectItem value="24">Last 24 months</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Show Annual Costs</Label>
                    <p className="text-xs text-muted-foreground">Display yearly totals in cards</p>
                  </div>
                  <Switch
                    checked={localSettings.recurring_show_annual ?? true}
                    onCheckedChange={(v) => updateSetting('recurring_show_annual', v)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Recurring AI Learning */}
            <Card>
              <CardHeader>
                <CardTitle>Recurring AI Learning</CardTitle>
                <CardDescription>Current learning progress and accuracy</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {recurringStatsLoading ? (
                  <div className="text-sm text-muted-foreground">Loading learning stats…</div>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-lg border p-3">
                      <div className="text-xs text-muted-foreground">Merchant memory</div>
                      <div className="text-lg font-semibold">
                        {recurringAiStats?.merchant_memory?.total_patterns ?? '—'}
                      </div>
                    </div>
                    <div className="rounded-lg border p-3">
                      <div className="text-xs text-muted-foreground">Feedback count</div>
                      <div className="text-lg font-semibold">
                        {recurringAiStats?.feedback?.total ?? '—'}
                      </div>
                    </div>
                  </div>
                )}
                {recurringAccuracy && Object.keys(recurringAccuracy).length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-muted-foreground">Accuracy by type</div>
                    <div className="grid gap-2 md:grid-cols-2">
                      {Object.entries(recurringAccuracy).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between rounded-lg border p-2 text-sm">
                          <span className="capitalize">{key.replace('_', ' ')}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {Math.round((value as number) * 100)}%
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Recurring Maintenance */}
            <Card>
              <CardHeader>
                <CardTitle>Recurring Maintenance</CardTitle>
                <CardDescription>Run cleanup and reclassification jobs</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <Button
                    variant="outline"
                    onClick={() => reclassifyRecurring.mutate()}
                    disabled={reclassifyRecurring.isPending}
                  >
                    {reclassifyRecurring.isPending ? "Reclassifying…" : "Reclassify All"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => mergeDuplicates.mutate()}
                    disabled={mergeDuplicates.isPending}
                  >
                    {mergeDuplicates.isPending ? "Merging…" : "Merge Duplicates"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => reclassifyWithLLM.mutate(100)}
                    disabled={reclassifyWithLLM.isPending}
                  >
                    {reclassifyWithLLM.isPending ? "Running LLM…" : "Reclassify with LLM"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => backfillMemory.mutate()}
                    disabled={backfillMemory.isPending}
                  >
                    {backfillMemory.isPending ? "Backfilling…" : "Backfill Memory"}
                  </Button>
                </div>
                <div className="rounded-lg border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Intelligence cache</span>
                    <span className="text-xs text-muted-foreground">
                      {intelligenceCacheStats?.total_entries ?? "—"} entries
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Hit rate</span>
                    <span className="text-xs text-muted-foreground">
                      {intelligenceCacheStats?.hit_rate ? `${Math.round(intelligenceCacheStats.hit_rate * 100)}%` : "—"}
                    </span>
                  </div>
                  <div className="mt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => cleanupCache.mutate(60)}
                      disabled={cleanupCache.isPending}
                    >
                      {cleanupCache.isPending ? "Cleaning…" : "Clean Cache (60d)"}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* System Info */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>About</CardTitle>
                <CardDescription>System information</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-1">
                    <span className="text-sm text-muted-foreground">Version</span>
                    <p className="font-medium">1.0.0</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-sm text-muted-foreground">Database</span>
                    <p className="font-medium">DuckDB</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-sm text-muted-foreground">AI Provider</span>
                    <p className="font-medium">{aiSettings?.ai_provider || 'auto'}</p>
                  </div>
                  <div className="space-y-1">
                    <span className="text-sm text-muted-foreground">Realtime</span>
                    <p className="font-medium">{localSettings.realtime_enabled ? 'Enabled' : 'Disabled'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* AI TAB */}
        <TabsContent value="ai" className="space-y-4">
          {/* AI Status Banner */}
          <Card className={`border-2 ${aiStatus?.ok ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'}`}>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {aiStatusLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin text-gray-500" />
                  ) : aiStatus?.ok ? (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-yellow-600" />
                  )}
                  <div>
                    <h3 className="font-medium">
                      AI Service: {aiStatus?.ok ? 'Connected' : 'Not Connected'}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {aiStatus?.provider || 'No provider configured'}
                      {aiStatus?.latency_ms ? ` • ${aiStatus.latency_ms}ms latency` : ''}
                      {aiStatus?.model ? ` • ${aiStatus.model}` : ''}
                    </p>
                    {/* Show suggestion if available */}
                    {aiStatus?.suggestion && !aiStatus?.ok && (
                      <p className="text-xs text-yellow-700 mt-1">
                        {aiStatus.suggestion}
                      </p>
                    )}
                    {/* Show error type and details */}
                    {aiStatus?.error_type && (
                      <p className="text-xs text-red-600 mt-1">
                        Error: {aiStatus.error_type} - {aiStatus.error}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {aiMetrics && (
                    <Badge variant="outline" className="mr-2">
                      {aiMetrics.accuracy_rate?.toFixed(0)}% accuracy
                    </Badge>
                  )}
                  {/* Show config info */}
                  {aiStatus?.config && (
                    <Badge variant="secondary" className="mr-2 text-xs">
                      {aiStatus.config.max_retries} retries • {aiStatus.config.timeout}s timeout
                    </Badge>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      aiPing.refetch()
                      refetchAIStatus()
                    }}
                    disabled={aiPing.isFetching}
                  >
                    {aiPing.isFetching ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                    <span className="ml-2">Test Connection</span>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* AI Auto-Categorization Status Card */}
          <Card className="border-2 border-primary/20">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  <CardTitle>Auto-Categorization</CardTitle>
                  {isCategorizationRunning && (
                    <Badge variant="default" className="ml-2">Running</Badge>
                  )}
                </div>
                {categorizationStatus?.overall?.uncategorized && categorizationStatus.overall.uncategorized > 0 && !isCategorizationRunning && (
                  <Button
                    size="sm"
                    onClick={() => categorizeAll.mutate({ batch_size: 50 })}
                    disabled={categorizeAll.isPending}
                  >
                    {categorizeAll.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="mr-2 h-4 w-4" />
                    )}
                    Categorize All ({categorizationStatus.overall.uncategorized})
                  </Button>
                )}
              </div>
              <CardDescription>
                Race-condition safe bulk categorization with job tracking
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Overall Progress */}
              <div className="grid grid-cols-4 gap-3">
                <div className="text-center p-3 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">
                    {categorizationStatus?.overall?.total_transactions?.toLocaleString() || '-'}
                  </div>
                  <div className="text-xs text-muted-foreground">Total</div>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {categorizationStatus?.overall?.categorized?.toLocaleString() || '-'}
                  </div>
                  <div className="text-xs text-green-600">Categorized</div>
                </div>
                <div className="text-center p-3 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">
                    {categorizationStatus?.overall?.uncategorized?.toLocaleString() || '-'}
                  </div>
                  <div className="text-xs text-orange-600">Uncategorized</div>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {categorizationStatus?.overall?.percent_complete?.toFixed(1) || '0'}%
                  </div>
                  <div className="text-xs text-blue-600">Complete</div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Coverage</span>
                  <span className="font-medium">{categorizationStatus?.overall?.percent_complete?.toFixed(1) || 0}%</span>
                </div>
                <Progress value={categorizationStatus?.overall?.percent_complete || 0} className="h-2" />
              </div>

              {/* Current Job Status */}
              {categorizationStatus?.current_job && (
                <div className={`p-4 rounded-lg border-2 ${
                  categorizationStatus.current_job.status === 'processing' ? 'bg-blue-50 border-blue-200' :
                  categorizationStatus.current_job.status === 'completed' ? 'bg-green-50 border-green-200' :
                  categorizationStatus.current_job.status === 'failed' ? 'bg-red-50 border-red-200' :
                  'bg-gray-50 border-gray-200'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {categorizationStatus.current_job.status === 'processing' && (
                        <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                      )}
                      {categorizationStatus.current_job.status === 'completed' && (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      )}
                      {categorizationStatus.current_job.status === 'failed' && (
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                      )}
                      <span className="font-medium">
                        {categorizationStatus.current_job.status === 'processing' ? 'Processing...' :
                         categorizationStatus.current_job.status === 'completed' ? 'Completed' :
                         categorizationStatus.current_job.status === 'failed' ? 'Failed' :
                         categorizationStatus.current_job.status}
                      </span>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      Job: {categorizationStatus.current_job.job_id?.slice(0, 8)}...
                    </Badge>
                  </div>

                  {categorizationStatus.current_job.status === 'processing' && (
                    <div className="space-y-2">
                      <Progress value={categorizationStatus.current_job.progress_percent || 0} className="h-3" />
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {categorizationStatus.current_job.processed || 0} / {categorizationStatus.current_job.total || 0} transactions
                        </span>
                        <span className="font-medium text-blue-600">
                          {categorizationStatus.current_job.progress_percent?.toFixed(1)}%
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {categorizationStatus.current_job.categorized || 0} categorized so far
                      </div>
                    </div>
                  )}

                  {categorizationStatus.current_job.status === 'completed' && (
                    <div className="text-sm text-green-700">
                      Successfully categorized {categorizationStatus.current_job.categorized || 0} of {categorizationStatus.current_job.total || 0} transactions
                    </div>
                  )}

                  {categorizationStatus.current_job.error_message && (
                    <div className="text-sm text-red-600 mt-2">
                      Error: {categorizationStatus.current_job.error_message}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Processing Queue Control Panel */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  <CardTitle>Processing Queue</CardTitle>
                </div>
                <div className="flex items-center gap-2">
                  {queueStats?.is_paused ? (
                    <Button
                      size="sm"
                      onClick={() => resumeAI.mutate()}
                      disabled={resumeAI.isPending}
                    >
                      {resumeAI.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Play className="mr-2 h-4 w-4" />
                      )}
                      Resume All
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => pauseAI.mutate()}
                      disabled={pauseAI.isPending}
                    >
                      {pauseAI.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Pause className="mr-2 h-4 w-4" />
                      )}
                      Pause All
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Queue Stats Bar */}
              <div className="grid grid-cols-6 gap-2">
                <div className="text-center p-2 bg-blue-50 rounded-lg">
                  <div className="text-lg font-bold text-blue-600">
                    {queueStatsLoading ? '-' : queueStats?.active || 0}
                  </div>
                  <div className="text-xs text-blue-600">Active</div>
                </div>
                <div className="text-center p-2 bg-yellow-50 rounded-lg">
                  <div className="text-lg font-bold text-yellow-600">
                    {queueStatsLoading ? '-' : queueStats?.pending || 0}
                  </div>
                  <div className="text-xs text-yellow-600">Pending</div>
                </div>
                <div className="text-center p-2 bg-orange-50 rounded-lg">
                  <div className="text-lg font-bold text-orange-600">
                    {queueStatsLoading ? '-' : queueStats?.paused || 0}
                  </div>
                  <div className="text-xs text-orange-600">Paused</div>
                </div>
                <div className="text-center p-2 bg-green-50 rounded-lg">
                  <div className="text-lg font-bold text-green-600">
                    {queueStatsLoading ? '-' : queueStats?.completed || 0}
                  </div>
                  <div className="text-xs text-green-600">Done</div>
                </div>
                <div className="text-center p-2 bg-red-50 rounded-lg">
                  <div className="text-lg font-bold text-red-600">
                    {queueStatsLoading ? '-' : queueStats?.failed || 0}
                  </div>
                  <div className="text-xs text-red-600">Failed</div>
                </div>
                <div className="text-center p-2 bg-gray-50 rounded-lg">
                  <div className="text-lg font-bold text-gray-600">
                    {queueStatsLoading ? '-' : queueStats?.cancelled || 0}
                  </div>
                  <div className="text-xs text-gray-600">Cancelled</div>
                </div>
              </div>

              {/* Global Pause Status */}
              {queueStats?.is_paused && (
                <Alert className="bg-orange-50 border-orange-200">
                  <Pause className="h-4 w-4 text-orange-600" />
                  <AlertDescription className="text-orange-800">
                    AI processing is paused. New imports will not trigger automatic categorization.
                  </AlertDescription>
                </Alert>
              )}

              {/* Running Jobs */}
              {bulkJobs && bulkJobs.length > 0 && (
                <div className="space-y-2">
                  <div className="text-sm font-medium">Recent Jobs</div>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {bulkJobs.map((job: any) => (
                      <div
                        key={job.job_id}
                        className={`p-3 border rounded-lg ${
                          job.status === 'processing' ? 'bg-blue-50 border-blue-200' :
                          job.status === 'completed' ? 'bg-green-50 border-green-200' :
                          job.status === 'failed' ? 'bg-red-50 border-red-200' :
                          job.status === 'paused' ? 'bg-orange-50 border-orange-200' :
                          'bg-gray-50'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            {job.status === 'processing' && <Loader2 className="h-4 w-4 animate-spin text-blue-600" />}
                            {job.status === 'completed' && <CheckCircle className="h-4 w-4 text-green-600" />}
                            {job.status === 'failed' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                            {job.status === 'paused' && <Pause className="h-4 w-4 text-orange-600" />}
                            <span className="font-medium text-sm">{job.job_type}</span>
                            <Badge variant="secondary" className="text-xs">
                              {job.status}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1">
                            {(job.status === 'processing' || job.status === 'pending' || job.status === 'paused') && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => cancelJob.mutate(job.job_id)}
                                disabled={cancelJob.isPending}
                              >
                                <X className="h-4 w-4 text-gray-500" />
                              </Button>
                            )}
                            {job.status === 'failed' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => retryJob.mutate(job.job_id)}
                                disabled={retryJob.isPending}
                              >
                                <RotateCcw className="h-4 w-4 text-blue-500" />
                              </Button>
                            )}
                          </div>
                        </div>
                        {job.status === 'processing' && (
                          <div className="space-y-1">
                            <Progress value={job.progress_percentage || 0} className="h-2" />
                            <div className="text-xs text-muted-foreground">
                              {job.processed_transactions || 0} / {job.total_transactions || 0} transactions
                            </div>
                          </div>
                        )}
                        {job.error_message && (
                          <div className="text-xs text-red-600 mt-1">{job.error_message}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Processing Settings */}
              <div className="pt-2 border-t">
                <div className="text-sm font-medium mb-3">Processing Settings</div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Batch Size ({localSettings.ai_batch_size || 20} transactions)</Label>
                    <Slider
                      value={[localSettings.ai_batch_size || 20]}
                      onValueChange={([v]) => {
                        updateSetting('ai_batch_size', v)
                        updateQueueSettings.mutate({ batch_size: v })
                      }}
                      min={5}
                      max={100}
                      step={5}
                    />
                    <p className="text-xs text-muted-foreground">Lower = less CPU usage</p>
                  </div>
                  <div className="space-y-2">
                    <Label>Batch Delay ({localSettings.ai_batch_delay_ms || 500}ms)</Label>
                    <Slider
                      value={[localSettings.ai_batch_delay_ms || 500]}
                      onValueChange={([v]) => {
                        updateSetting('ai_batch_delay_ms', v)
                        updateQueueSettings.mutate({ batch_delay_ms: v })
                      }}
                      min={0}
                      max={5000}
                      step={100}
                    />
                    <p className="text-xs text-muted-foreground">Higher = more throttling</p>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-4">
                  <div className="space-y-0.5">
                    <Label>Auto-start on Import</Label>
                    <p className="text-xs text-muted-foreground">Automatically process new imports</p>
                  </div>
                  <Switch
                    checked={localSettings.ai_auto_start_on_import ?? true}
                    onCheckedChange={(v) => {
                      updateSetting('ai_auto_start_on_import', v)
                      updateQueueSettings.mutate({ auto_start_on_import: v })
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
            {/* AI Provider & Model Config */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  AI Provider
                </CardTitle>
                <CardDescription>Configure AI service connection</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <Select
                    value={localSettings.ai_provider || 'auto'}
                    onValueChange={(v) => {
                      updateSetting('ai_provider', v)
                      handleSaveAISettings({ ai_provider: v })
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto (LM Studio → OpenAI → Local)</SelectItem>
                      <SelectItem value="lmstudio">LM Studio Only</SelectItem>
                      <SelectItem value="openai">OpenAI Only</SelectItem>
                      <SelectItem value="local">Local Heuristics Only</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Auto mode tries providers in order with fallback
                  </p>
                </div>

                {/* OpenAI Configuration */}
                <div className="pt-2 border-t">
                  <div className="text-sm font-medium mb-3">OpenAI / Compatible API</div>
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label>API Key</Label>
                      <Input
                        type="password"
                        value={openAiKeyInput}
                        onChange={(e) => {
                          setOpenAiKeyInput(e.target.value)
                          setHasChanges(true)
                        }}
                        placeholder="sk-..."
                      />
                      <p className="text-xs text-muted-foreground">
                        OpenAI API key (or compatible service)
                      </p>
                      {openAiKeySet ? (
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>API key is set</span>
                          <Button type="button" variant="ghost" size="sm" onClick={handleClearOpenAiKey}>
                            Clear
                          </Button>
                        </div>
                      ) : null}
                    </div>
                    <div className="space-y-2">
                      <Label>Base URL (Optional)</Label>
                      <Input
                        value={localSettings.ai_openai_base_url || ''}
                        onChange={(e) => updateSetting('ai_openai_base_url', e.target.value)}
                        placeholder="https://api.openai.com/v1 (default)"
                      />
                      <p className="text-xs text-muted-foreground">
                        Leave blank for OpenAI, or use custom endpoint
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label>Model</Label>
                      <Input
                        value={localSettings.ai_openai_model || ''}
                        onChange={(e) => updateSetting('ai_openai_model', e.target.value)}
                        placeholder="gpt-4o-mini (default)"
                      />
                    </div>
                  </div>
                </div>

                {/* LM Studio Configuration */}
                <div className="pt-2 border-t">
                  <div className="text-sm font-medium mb-3">LM Studio (Local)</div>
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label>Server URL</Label>
                      <Input
                        value={localSettings.ai_lmstudio_base_url || 'http://127.0.0.1:1234/v1'}
                        onChange={(e) => updateSetting('ai_lmstudio_base_url', e.target.value)}
                        placeholder="http://127.0.0.1:1234/v1"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Model Override</Label>
                      <Input
                        value={localSettings.ai_lmstudio_model || ''}
                        onChange={(e) => updateSetting('ai_lmstudio_model', e.target.value)}
                        placeholder="Auto-detect from server"
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Advanced AI Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5" />
                  Advanced Settings
                </CardTitle>
                <CardDescription>Timeout, retry, and rate limiting</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Request Timeout ({localSettings.ai_timeout || 30}s)</Label>
                    <Slider
                      value={[localSettings.ai_timeout || 30]}
                      onValueChange={([v]) => updateSetting('ai_timeout', v)}
                      min={5}
                      max={120}
                      step={5}
                    />
                    <p className="text-xs text-muted-foreground">
                      How long to wait for AI response
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>Max Retries ({localSettings.ai_max_retries || 3})</Label>
                    <Slider
                      value={[localSettings.ai_max_retries || 3]}
                      onValueChange={([v]) => updateSetting('ai_max_retries', v)}
                      min={0}
                      max={5}
                      step={1}
                    />
                    <p className="text-xs text-muted-foreground">
                      Retries on rate limit or timeout
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Max Concurrent ({localSettings.ai_max_concurrency || 2})</Label>
                    <Slider
                      value={[localSettings.ai_max_concurrency || 2]}
                      onValueChange={([v]) => updateSetting('ai_max_concurrency', v)}
                      min={1}
                      max={10}
                      step={1}
                    />
                    <p className="text-xs text-muted-foreground">
                      Parallel AI requests
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>Temperature ({(localSettings.ai_temperature || 0.1).toFixed(1)})</Label>
                    <Slider
                      value={[(localSettings.ai_temperature || 0.1) * 10]}
                      onValueChange={([v]) => updateSetting('ai_temperature', v / 10)}
                      min={0}
                      max={10}
                      step={1}
                    />
                    <p className="text-xs text-muted-foreground">
                      Lower = more consistent
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="space-y-0.5">
                    <Label>Retry with Jitter</Label>
                    <p className="text-xs text-muted-foreground">
                      Add randomness to retry delays (recommended)
                    </p>
                  </div>
                  <Switch
                    checked={localSettings.ai_retry_jitter ?? true}
                    onCheckedChange={(v) => updateSetting('ai_retry_jitter', v)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Debug Mode</Label>
                    <p className="text-xs text-muted-foreground">
                      Log AI prompts and responses
                    </p>
                  </div>
                  <Switch
                    checked={localSettings.ai_debug ?? false}
                    onCheckedChange={(v) => updateSetting('ai_debug', v)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* AI Behavior */}
            <Card>
              <CardHeader>
                <CardTitle>AI Behavior</CardTitle>
                <CardDescription>Configure automatic categorization</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Auto-categorize on Import</Label>
                    <p className="text-xs text-muted-foreground">Run AI on new transactions</p>
                  </div>
                  <Switch
                    checked={localSettings.ai_auto_categorize_on_import ?? true}
                    onCheckedChange={(v) => {
                      updateSetting('ai_auto_categorize_on_import', v)
                      handleSaveAISettings({ ai_auto_categorize_on_import: v })
                    }}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Min Confidence to Auto-Apply ({((localSettings.ai_auto_categorize_min_conf || 0.7) * 100).toFixed(0)}%)</Label>
                  <Slider
                    value={[(localSettings.ai_auto_categorize_min_conf || 0.7) * 100]}
                    onValueChange={([v]) => {
                      updateSetting('ai_auto_categorize_min_conf', v / 100)
                    }}
                    min={50}
                    max={95}
                    step={5}
                  />
                  <p className="text-xs text-muted-foreground">
                    AI suggestions below this are marked for review
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Auto-create Rules</Label>
                    <p className="text-xs text-muted-foreground">Create rules from patterns</p>
                  </div>
                  <Switch
                    checked={localSettings.ai_auto_create_rules ?? false}
                    onCheckedChange={(v) => updateSetting('ai_auto_create_rules', v)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Anomaly Detection Threshold ({((localSettings.ai_anomaly_min_conf || 0.8) * 100).toFixed(0)}%)</Label>
                  <Slider
                    value={[(localSettings.ai_anomaly_min_conf || 0.8) * 100]}
                    onValueChange={([v]) => updateSetting('ai_anomaly_min_conf', v / 100)}
                    min={50}
                    max={95}
                    step={5}
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  variant="ghost"
                  onClick={handleResetAI}
                  disabled={resetAI.isPending}
                >
                  {resetAI.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-2 h-4 w-4" />
                  )}
                  Reset AI Fields
                </Button>
              </CardFooter>
            </Card>

            {/* Merchant Memory */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  Merchant Memory
                </CardTitle>
                <CardDescription>
                  {merchantMemory?.length || 0} patterns learned
                </CardDescription>
              </CardHeader>
              <CardContent>
                {memoryLoading ? (
                  <div className="flex justify-center p-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : merchantMemory?.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Sparkles className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No learned patterns yet.</p>
                    <p className="text-xs">Categorize transactions to teach the AI.</p>
                  </div>
                ) : (
                  <div className="max-h-[250px] overflow-y-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Pattern</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {merchantMemory?.slice(0, 15).map((mapping: any, i: number) => (
                          <TableRow key={i}>
                            <TableCell className="font-mono text-xs truncate max-w-[120px]">
                              {mapping.pattern || mapping.merchant_pattern}
                            </TableCell>
                            <TableCell>
                              <Badge variant="secondary" className="text-xs">
                                {mapping.category_name || mapping.category}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteMemory(mapping.pattern || mapping.merchant_pattern)}
                                disabled={deleteMerchantMemory.isPending}
                              >
                                <Trash2 className="h-3 w-3 text-red-500" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
              {merchantMemory && merchantMemory.length > 15 && (
                <CardFooter>
                  <p className="text-xs text-muted-foreground">
                    Showing 15 of {merchantMemory.length} patterns
                  </p>
                </CardFooter>
              )}
            </Card>
          </div>
        </TabsContent>

        {/* BUDGET TAB */}
        <TabsContent value="budget">
          <BudgetSettingsTab />
        </TabsContent>

        {/* DASHBOARD TAB */}
        <TabsContent value="dashboard">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LayoutDashboard className="h-5 w-5" />
                  Dashboard Preferences
                </CardTitle>
                <CardDescription>Customize your dashboard experience</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Default Time Period</Label>
                  <Select
                    value={localSettings.dashboard_default_period || '30d'}
                    onValueChange={(v) => updateSetting('dashboard_default_period', v)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7d">Last 7 days</SelectItem>
                      <SelectItem value="30d">Last 30 days</SelectItem>
                      <SelectItem value="90d">Last 90 days</SelectItem>
                      <SelectItem value="365d">Last year</SelectItem>
                      <SelectItem value="all">All time</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Show AI Insights</Label>
                    <p className="text-xs text-muted-foreground">Display AI-powered insights on dashboard</p>
                  </div>
                  <Switch
                    checked={localSettings.dashboard_show_ai ?? true}
                    onCheckedChange={(v) => updateSetting('dashboard_show_ai', v)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Realtime Updates</Label>
                    <p className="text-xs text-muted-foreground">Enable WebSocket updates</p>
                  </div>
                  <Switch
                    checked={localSettings.realtime_enabled ?? false}
                    onCheckedChange={(v) => updateSetting('realtime_enabled', v)}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Performance</CardTitle>
                <CardDescription>System performance settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>DuckDB Threads</Label>
                  <Input
                    type="number"
                    value={localSettings.duckdb_threads || 0}
                    onChange={(e) => updateSetting('duckdb_threads', parseInt(e.target.value) || 0)}
                    min={0}
                    max={16}
                  />
                  <p className="text-xs text-muted-foreground">
                    0 = auto-detect (uses all cores)
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* DATA TAB */}
        <TabsContent value="data" className="space-y-4">
          {/* Stats Row */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Transactions</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {statsLoading ? '-' : (stats?.transactions || 0).toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Categories</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {statsLoading ? '-' : stats?.categories || 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Rules</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {statsLoading ? '-' : stats?.rules || 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">DB Size</CardTitle>
                <HardDrive className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {statsLoading ? '-' : formatBytes(stats?.db_size_bytes || 0)}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Actions */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Export & Backup</CardTitle>
                <CardDescription>Download your data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <div className="font-medium">Export Transactions CSV</div>
                    <div className="text-sm text-muted-foreground">
                      Download all transactions as CSV
                    </div>
                  </div>
                  <Button variant="outline" onClick={handleExport}>
                    <FileDown className="mr-2 h-4 w-4" />
                    Export
                  </Button>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <div className="font-medium">Create Database Backup</div>
                    <div className="text-sm text-muted-foreground">
                      Save a complete backup of your database
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleBackup}
                    disabled={createBackup.isPending}
                  >
                    {createBackup.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="mr-2 h-4 w-4" />
                    )}
                    Backup
                  </Button>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <div className="font-medium">Optimize Database</div>
                    <div className="text-sm text-muted-foreground">
                      Run VACUUM and optimize performance
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleOptimize}
                    disabled={optimizeDb.isPending}
                  >
                    {optimizeDb.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    Optimize
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Danger Zone */}
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <AlertTriangle className="h-5 w-5" />
                  Danger Zone
                </CardTitle>
                <CardDescription>Irreversible actions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert variant="destructive" className="bg-red-50 border-red-200">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="text-red-800">
                    These actions cannot be undone. A backup will be created before reset.
                  </AlertDescription>
                </Alert>

                <div className="p-4 border border-red-200 bg-red-50 rounded-lg space-y-3">
                  <div>
                    <div className="font-medium text-red-900">Factory Reset</div>
                    <div className="text-sm text-red-700">
                      Wipe all data and start fresh
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder='Type "FACTORY RESET" to confirm'
                      value={confirmReset}
                      onChange={(e) => setConfirmReset(e.target.value)}
                      className="flex-1 bg-white"
                    />
                    <Button
                      variant="destructive"
                      onClick={handleFactoryReset}
                      disabled={confirmReset !== 'FACTORY RESET' || factoryReset.isPending}
                    >
                      {factoryReset.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        'Reset'
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
      <ConfirmDialog />
    </div>
  )
}
