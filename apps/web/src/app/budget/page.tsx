'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import {
  Plus,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  PiggyBank,
  Sparkles,
  DollarSign,
  Wallet,
  Lock,
  Unlock,
  RefreshCw,
  Zap,
  AlertCircle,
  XCircle,
  ArrowRight,
  Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { PageHeader } from '@/components/ui/page-header'
import {
  useIncome,
  useDetectIncome,
  useBudgetSuggestion,
  useApplySuggestion,
  useBudgetPace,
  useBudgetBreakdown,
  useBudgetInsights,
  type IncomeSource,
  type BudgetSuggestion,
  type CategorySuggestion,
  type PaceWarning,
} from '@/hooks/useBudgetIntelligence'

interface BudgetCategory {
  id: string
  category_id: string
  category_name: string
  amount_limit: number
  rollover: boolean
  spent: number
  remaining: number
  percent_used: number
  is_committed?: boolean
}

interface Budget {
  id: string
  name: string
  period: string
  start_date?: string
  is_active: boolean
  created_at: string
  total_limit: number
  total_spent: number
  categories: BudgetCategory[]
  auto_suggested?: boolean
}

interface BudgetProgress {
  budget_id: string
  budget_name: string
  period_start: string
  period_end: string
  days_remaining: number
  total_limit: number
  total_spent: number
  total_remaining: number
  percent_used: number
  categories: BudgetCategory[]
  on_track: boolean
}

function useBudgets() {
  return useQuery({
    queryKey: ['budgets'],
    queryFn: async () => {
      const { data, error } = await client.get<Budget[]>('/api/budgets')
      if (error) throw error
      return data || []
    },
  })
}

function useBudgetProgress(budgetId: string) {
  return useQuery({
    queryKey: ['budgets', budgetId, 'progress'],
    queryFn: async () => {
      const { data, error } = await client.get<BudgetProgress>(`/api/budgets/${budgetId}/progress`)
      if (error) throw error
      return data
    },
    enabled: !!budgetId,
  })
}

// Income Source Card
function IncomeSourceCard({ source }: { source: IncomeSource }) {
  const getFrequencyLabel = (freq: string) => {
    switch (freq) {
      case 'weekly': return 'Weekly'
      case 'biweekly': return 'Bi-weekly'
      case 'monthly': return 'Monthly'
      case 'irregular': return 'Irregular'
      default: return freq
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'salary': return <Wallet className="h-4 w-4" />
      case 'side_income': return <Zap className="h-4 w-4" />
      case 'investment': return <TrendingUp className="h-4 w-4" />
      default: return <DollarSign className="h-4 w-4" />
    }
  }

  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-green-100 rounded-full text-green-600">
          {getTypeIcon(source.type)}
        </div>
        <div>
          <div className="font-medium">{source.name}</div>
          <div className="text-xs text-muted-foreground">
            {getFrequencyLabel(source.frequency)} &bull; {(source.confidence * 100).toFixed(0)}% confidence
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className="font-semibold text-green-600">
          +${source.avg_amount.toFixed(2)}
        </div>
        <div className="text-xs text-muted-foreground">
          {source.occurrence_count || 0} transactions
        </div>
      </div>
    </div>
  )
}

// Pace Warning Banner
function PaceWarningBanner({ budgetId }: { budgetId: string }) {
  const { data: pace, isLoading } = useBudgetPace(budgetId)

  if (isLoading || !pace) return null

  const criticalWarnings = pace.warnings?.filter(
    (w) => w.status === 'will_exceed' || w.status === 'exceeded'
  ) || []

  if (criticalWarnings.length === 0) return null

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="font-medium text-amber-800">Spending Pace Warnings</h4>
          <div className="mt-2 space-y-2">
            {criticalWarnings.slice(0, 3).map((warning) => (
              <div key={warning.category_id} className="text-sm text-amber-700">
                <span className="font-medium">{warning.category_name}:</span> {warning.message}
              </div>
            ))}
          </div>
          {criticalWarnings.length > 3 && (
            <div className="text-xs text-amber-600 mt-2">
              +{criticalWarnings.length - 3} more warnings
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Category Suggestion Item
function CategorySuggestionItem({ suggestion }: { suggestion: CategorySuggestion }) {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return <TrendingUp className="h-3 w-3 text-red-500" />
      case 'decreasing': return <TrendingDown className="h-3 w-3 text-green-500" />
      default: return null
    }
  }

  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <div className="flex items-center gap-2">
        {suggestion.is_committed ? (
          <Lock className="h-3 w-3 text-muted-foreground" />
        ) : (
          <Unlock className="h-3 w-3 text-muted-foreground" />
        )}
        <span className="text-sm">{suggestion.category_name}</span>
        {getTrendIcon(suggestion.trend)}
      </div>
      <div className="text-right">
        <div className="text-sm font-medium">${suggestion.suggested_limit.toFixed(0)}</div>
        <div className="text-xs text-muted-foreground">
          avg ${suggestion.avg_spending.toFixed(0)}
        </div>
      </div>
    </div>
  )
}

// Smart Budget Wizard Dialog
function SmartBudgetWizard({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(1)
  const [savingsPercent, setSavingsPercent] = useState(20)
  const [customName, setCustomName] = useState('')

  const { data: income, isLoading: incomeLoading } = useIncome()
  const detectIncome = useDetectIncome()
  const { data: suggestion, isLoading: suggestionLoading, refetch: refetchSuggestion } = useBudgetSuggestion(savingsPercent / 100)
  const applySuggestion = useApplySuggestion()
  const queryClient = useQueryClient()

  const totalMonthlyIncome = (income || []).reduce((sum, src) => {
    if (src.is_active === false) return sum
    switch (src.frequency) {
      case 'weekly': return sum + src.avg_amount * 4.33
      case 'biweekly': return sum + src.avg_amount * 2.17
      case 'monthly': return sum + src.avg_amount
      case 'irregular': return sum + src.avg_amount * 0.5
      default: return sum + src.avg_amount
    }
  }, 0)

  const handleDetectIncome = async () => {
    await detectIncome.mutateAsync()
  }

  const handleApply = async () => {
    if (!suggestion) return
    await applySuggestion.mutateAsync({
      suggestionId: suggestion.id,
      customName: customName || undefined,
    })
    queryClient.invalidateQueries({ queryKey: ['budgets'] })
    setOpen(false)
    setStep(1)
    onCreated()
  }

  const resetWizard = () => {
    setStep(1)
    setSavingsPercent(20)
    setCustomName('')
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetWizard(); }}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Sparkles className="h-4 w-4" />
          Smart Budget
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Smart Budget Wizard
          </DialogTitle>
          <DialogDescription>
            {step === 1 && "Let's analyze your income to create a personalized budget."}
            {step === 2 && "Set your savings goal and we'll suggest spending limits."}
            {step === 3 && "Review and customize your smart budget suggestion."}
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 py-4">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors",
                step >= s
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {s}
            </div>
          ))}
        </div>

        {/* Step 1: Income Detection */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">Detected Income Sources</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDetectIncome}
                disabled={detectIncome.isPending}
              >
                {detectIncome.isPending ? (
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Re-detect
              </Button>
            </div>

            {incomeLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Analyzing your transactions...
              </div>
            ) : income && Array.isArray(income) && income.length > 0 ? (
              <div className="space-y-2">
                {income.filter(s => s.is_active !== false).map((source) => (
                  <IncomeSourceCard key={source.id} source={source} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <DollarSign className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No income detected yet.</p>
                <Button
                  className="mt-4"
                  onClick={handleDetectIncome}
                  disabled={detectIncome.isPending}
                >
                  Detect Income
                </Button>
              </div>
            )}

            {income && Array.isArray(income) && income.length > 0 && (
              <Card className="bg-green-50 border-green-200">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-green-800">Estimated Monthly Income</span>
                    <span className="text-2xl font-bold text-green-600">
                      ${totalMonthlyIncome.toFixed(2)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end pt-4">
              <Button
                onClick={() => { setStep(2); refetchSuggestion(); }}
                disabled={!income || !Array.isArray(income) || income.length === 0}
              >
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Savings Goal */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <Label>Savings Goal</Label>
              <p className="text-sm text-muted-foreground mb-4">
                What percentage of your income would you like to save?
              </p>
              <div className="space-y-4">
                <Slider
                  value={[savingsPercent]}
                  onValueChange={([v]) => setSavingsPercent(v)}
                  min={5}
                  max={50}
                  step={5}
                />
                <div className="flex justify-between text-sm">
                  <span>5%</span>
                  <span className="font-medium text-primary">{savingsPercent}%</span>
                  <span>50%</span>
                </div>
              </div>
            </div>

            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-blue-600">Monthly Savings</div>
                    <div className="text-xl font-bold text-blue-800">
                      ${(totalMonthlyIncome * savingsPercent / 100).toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-blue-600">Available for Spending</div>
                    <div className="text-xl font-bold text-blue-800">
                      ${(totalMonthlyIncome * (100 - savingsPercent) / 100).toFixed(2)}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button onClick={() => { setStep(3); refetchSuggestion(); }}>
                Generate Budget
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Review Suggestion */}
        {step === 3 && (
          <div className="space-y-4">
            {suggestionLoading ? (
              <div className="text-center py-8">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Generating your smart budget...</p>
              </div>
            ) : suggestion ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="budget-name">Budget Name (optional)</Label>
                  <Input
                    id="budget-name"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder={suggestion.name}
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-sm text-muted-foreground">Income</div>
                      <div className="text-lg font-bold text-green-600">
                        ${suggestion.total_income.toFixed(0)}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-sm text-muted-foreground">Budget</div>
                      <div className="text-lg font-bold">
                        ${suggestion.suggested_total.toFixed(0)}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-sm text-muted-foreground">Savings</div>
                      <div className="text-lg font-bold text-blue-600">
                        ${suggestion.savings_target.toFixed(0)}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Category Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-60 overflow-y-auto">
                      {suggestion.categories.map((cat) => (
                        <CategorySuggestionItem key={cat.category_id} suggestion={cat} />
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <Info className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <p className="text-xs text-muted-foreground">
                    Categories marked with <Lock className="h-3 w-3 inline" /> are committed expenses
                    (recurring bills). Flexible categories can be adjusted as needed.
                  </p>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Unable to generate suggestion. Please try again.
              </div>
            )}

            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button
                onClick={handleApply}
                disabled={!suggestion || applySuggestion.isPending}
              >
                {applySuggestion.isPending ? 'Creating...' : 'Create Budget'}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// Manual Budget Dialog
function CreateBudgetDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post<Budget>('/api/budgets', {
        body: { name, period: 'monthly', categories: [] }
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      setOpen(false)
      setName('')
      onCreated()
    },
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Plus className="mr-2 h-4 w-4" />
          Manual Budget
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Manual Budget</DialogTitle>
          <DialogDescription>
            Create a budget from scratch and add categories manually.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Budget Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Monthly Expenses"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!name || createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// Enhanced Budget Card with Pace
function BudgetCardEnhanced({ budget }: { budget: Budget }) {
  const { data: progress } = useBudgetProgress(budget.id)
  const { data: pace } = useBudgetPace(budget.id)
  const { data: breakdown } = useBudgetBreakdown(budget.id)

  const percentUsed = progress?.percent_used || 0
  const isOverBudget = percentUsed > 100
  const isWarning = percentUsed > 80 && percentUsed <= 100

  const getStatusBadge = () => {
    if (!pace) {
      return progress?.on_track ? (
        <Badge variant="default" className="bg-green-100 text-green-800 hover:bg-green-100">
          <CheckCircle className="mr-1 h-3 w-3" />
          On Track
        </Badge>
      ) : (
        <Badge variant="destructive">
          <AlertTriangle className="mr-1 h-3 w-3" />
          Over Budget
        </Badge>
      )
    }

    switch (pace.overall_status) {
      case 'on_track':
        return (
          <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
            <CheckCircle className="mr-1 h-3 w-3" />
            On Track
          </Badge>
        )
      case 'at_risk':
        return (
          <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
            <AlertCircle className="mr-1 h-3 w-3" />
            At Risk
          </Badge>
        )
      case 'will_exceed':
        return (
          <Badge className="bg-orange-100 text-orange-800 hover:bg-orange-100">
            <AlertTriangle className="mr-1 h-3 w-3" />
            Will Exceed
          </Badge>
        )
      case 'exceeded':
        return (
          <Badge variant="destructive">
            <XCircle className="mr-1 h-3 w-3" />
            Exceeded
          </Badge>
        )
      default:
        return null
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            {budget.name}
            {budget.auto_suggested && (
              <Sparkles className="h-3 w-3 text-primary" />
            )}
          </CardTitle>
          <CardDescription className="text-xs">
            {budget.period} budget
            {progress?.days_remaining !== undefined && (
              <> &bull; {progress.days_remaining} days left</>
            )}
          </CardDescription>
        </div>
        {getStatusBadge()}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Pace Warning */}
        {pace && pace.warnings && pace.warnings.length > 0 && (
          <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
            {pace.warnings[0].message}
          </div>
        )}

        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              ${progress?.total_spent?.toFixed(2) || '0.00'} spent
            </span>
            <span className="font-medium">
              ${progress?.total_limit?.toFixed(2) || budget.total_limit?.toFixed(2) || '0.00'}
            </span>
          </div>
          <Progress
            value={Math.min(percentUsed, 100)}
            className={cn(
              "h-2",
              isOverBudget && "[&>div]:bg-red-500",
              isWarning && "[&>div]:bg-amber-500"
            )}
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{percentUsed.toFixed(0)}% used</span>
            <span>${progress?.total_remaining?.toFixed(2) || '0.00'} remaining</span>
          </div>
        </div>

        {/* Committed vs Flexible */}
        {breakdown && breakdown.totals && (
          <div className="grid grid-cols-2 gap-2 pt-2 border-t">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                <Lock className="h-3 w-3" />
                Committed
              </div>
              <div className="font-medium">${(breakdown.totals.committed_limit ?? 0).toFixed(0)}</div>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                <Unlock className="h-3 w-3" />
                Flexible
              </div>
              <div className="font-medium">${((breakdown.totals.flexible_limit ?? 0) - (breakdown.totals.flexible_spent ?? 0)).toFixed(0)}</div>
            </div>
          </div>
        )}

        {/* Category Breakdown */}
        {progress?.categories && progress.categories.length > 0 && (
          <div className="space-y-2 pt-2 border-t">
            <div className="text-sm font-medium">Categories</div>
            {progress.categories.slice(0, 5).map((cat) => (
              <div key={cat.id} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="truncate max-w-[60%] flex items-center gap-1">
                    {cat.is_committed && <Lock className="h-2 w-2" />}
                    {cat.category_name}
                  </span>
                  <span className="text-muted-foreground">
                    ${cat.spent.toFixed(0)} / ${cat.amount_limit.toFixed(0)}
                  </span>
                </div>
                <Progress
                  value={Math.min(cat.percent_used, 100)}
                  className={cn(
                    "h-1",
                    cat.percent_used > 100 && "[&>div]:bg-red-500",
                    cat.percent_used > 80 && cat.percent_used <= 100 && "[&>div]:bg-amber-500"
                  )}
                />
              </div>
            ))}
            {progress.categories.length > 5 && (
              <div className="text-xs text-muted-foreground text-center">
                +{progress.categories.length - 5} more categories
              </div>
            )}
          </div>
        )}

        {(!progress?.categories || progress.categories.length === 0) && (
          <div className="text-sm text-muted-foreground text-center py-4">
            No category limits set yet
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Budget Insights Panel
function BudgetInsightsPanel() {
  const { data: insights, isLoading } = useBudgetInsights(6)

  if (isLoading) return null
  if (!insights || insights.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          Budget Insights
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {insights.map((insight: any, i: number) => (
            <div key={i} className="flex gap-3 p-2 rounded-lg hover:bg-muted/50">
              <div className={cn(
                "p-2 rounded-full h-fit",
                insight.priority === 'high' ? 'bg-red-100 text-red-600' :
                insight.priority === 'medium' ? 'bg-amber-100 text-amber-600' :
                'bg-blue-100 text-blue-600'
              )}>
                <Zap className="h-3 w-3" />
              </div>
              <div>
                <p className="text-sm">{insight.text}</p>
                {insight.action && (
                  <p className="text-xs text-primary mt-1">{insight.action}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default function BudgetPage() {
  const { data: budgets, isLoading, refetch } = useBudgets()
  const { data: income } = useIncome()

  const totalMonthlyIncome = (income || []).reduce((sum, src) => {
    if (src.is_active === false) return sum
    switch (src.frequency) {
      case 'weekly': return sum + src.avg_amount * 4.33
      case 'biweekly': return sum + src.avg_amount * 2.17
      case 'monthly': return sum + src.avg_amount
      case 'irregular': return sum + src.avg_amount * 0.5
      default: return sum + src.avg_amount
    }
  }, 0)

  const totalBudget = budgets?.reduce((sum, b) => sum + (b.total_limit || 0), 0) || 0
  const totalSpent = budgets?.reduce((sum, b) => sum + (b.total_spent || 0), 0) || 0
  const totalRemaining = totalBudget - totalSpent

  const activeBudget = budgets?.find(b => b.is_active)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Budget"
        description="AI-powered budget management and tracking."
        helpItems={[
          "Use 'Smart Budget' to auto-generate a budget based on your income and spending patterns",
          "Click any budget card to see detailed category breakdowns",
          "The pace indicator shows if you're on track to stay within budget",
          "Committed expenses (bills) are locked; flexible categories can be adjusted",
          "Budget suggestions refresh based on your income sources and historical spending"
        ]}
        action={
          <div className="flex gap-2">
            <CreateBudgetDialog onCreated={() => refetch()} />
            <SmartBudgetWizard onCreated={() => refetch()} />
          </div>
        }
      />

      {/* Pace Warning Banner for Active Budget */}
      {activeBudget && <PaceWarningBanner budgetId={activeBudget.id} />}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Income</CardTitle>
            <DollarSign className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${totalMonthlyIncome.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              {(income || []).filter(s => s.is_active !== false).length} income sources
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Budget</CardTitle>
            <PiggyBank className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalBudget.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              Across {budgets?.length || 0} budgets
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Spent</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalSpent.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">
              {totalBudget > 0 ? ((totalSpent / totalBudget) * 100).toFixed(0) : 0}% of budget
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Remaining</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              totalRemaining < 0 && "text-red-600"
            )}>
              ${totalRemaining.toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground">
              {totalRemaining >= 0 ? 'Left to spend' : 'Over budget'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Budgets Grid */}
        <div className="lg:col-span-2">
          {isLoading ? (
            <div className="text-center py-12 text-muted-foreground">
              Loading budgets...
            </div>
          ) : budgets && budgets.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {budgets.map((budget) => (
                <BudgetCardEnhanced key={budget.id} budget={budget} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Sparkles className="h-12 w-12 text-primary mb-4" />
                <h3 className="text-lg font-semibold">No budgets yet</h3>
                <p className="text-sm text-muted-foreground text-center max-w-sm mt-1 mb-4">
                  Use Smart Budget to automatically create a budget based on your income and spending patterns.
                </p>
                <SmartBudgetWizard onCreated={() => refetch()} />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Insights Sidebar */}
        <div className="space-y-4">
          <BudgetInsightsPanel />

          {/* Income Summary */}
          {income && Array.isArray(income) && income.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Income Sources</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {income.filter(s => s.is_active !== false).slice(0, 3).map((source) => (
                  <div key={source.id} className="flex items-center justify-between text-sm">
                    <span className="truncate">{source.name}</span>
                    <span className="text-green-600 font-medium">
                      +${source.avg_amount.toFixed(0)}
                    </span>
                  </div>
                ))}
                {income.filter(s => s.is_active !== false).length > 3 && (
                  <div className="text-xs text-muted-foreground text-center">
                    +{income.filter(s => s.is_active !== false).length - 3} more sources
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
