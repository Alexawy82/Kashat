'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import {
  PiggyBank,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  XCircle,
  ArrowRight,
  Sparkles,
  Lock,
  Unlock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { useBudgetPace, useBudgetBreakdown } from '@/hooks/useBudgetIntelligence'

interface Budget {
  id: string
  name: string
  period: string
  is_active: boolean
  total_limit: number
  total_spent: number
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

function BudgetStatusBadge({ status }: { status: string }) {
  switch (status) {
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

function ActiveBudgetDisplay({ budget }: { budget: Budget }) {
  const { data: progress } = useBudgetProgress(budget.id)
  const { data: pace } = useBudgetPace(budget.id)
  const { data: breakdown } = useBudgetBreakdown(budget.id)

  const percentUsed = progress?.percent_used || 0
  const isOverBudget = percentUsed > 100
  const isWarning = percentUsed > 80 && percentUsed <= 100

  const status = pace?.overall_status || (progress?.on_track ? 'on_track' : 'exceeded')

  return (
    <div className="space-y-4">
      {/* Header with status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-medium">{budget.name}</span>
          {budget.auto_suggested && (
            <Sparkles className="h-3 w-3 text-primary" />
          )}
        </div>
        <BudgetStatusBadge status={status} />
      </div>

      {/* Warning message if any */}
      {pace?.warnings && pace.warnings.length > 0 && (
        <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
          {pace.warnings[0].message}
        </div>
      )}

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">
            ${progress?.total_spent?.toFixed(0) || '0'} spent
          </span>
          <span className="font-medium">
            ${progress?.total_limit?.toFixed(0) || budget.total_limit?.toFixed(0) || '0'}
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
          <span>
            {progress?.days_remaining !== undefined && `${progress.days_remaining} days left`}
          </span>
        </div>
      </div>

      {/* Committed vs Flexible breakdown */}
      {breakdown && breakdown.totals && (
        <div className="grid grid-cols-2 gap-2 pt-2 border-t">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
              <Lock className="h-3 w-3" />
              Committed
            </div>
            <div className="font-medium text-sm">${(breakdown.totals.committed_limit ?? 0).toFixed(0)}</div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
              <Unlock className="h-3 w-3" />
              Flexible Left
            </div>
            <div className="font-medium text-sm">${((breakdown.totals.flexible_limit ?? 0) - (breakdown.totals.flexible_spent ?? 0)).toFixed(0)}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export function BudgetSummaryCard() {
  const { data: budgets, isLoading } = useBudgets()

  const activeBudget = budgets?.find(b => b.is_active)

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <PiggyBank className="h-4 w-4" />
            Budget
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-muted rounded w-3/4"></div>
            <div className="h-2 bg-muted rounded w-full"></div>
            <div className="h-3 bg-muted rounded w-1/2"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <PiggyBank className="h-4 w-4" />
          Budget
        </CardTitle>
        <Link href="/budget">
          <Button variant="ghost" size="sm" className="h-8 text-xs">
            View All
            <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {activeBudget ? (
          <ActiveBudgetDisplay budget={activeBudget} />
        ) : budgets && budgets.length > 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              You have {budgets.length} budget{budgets.length > 1 ? 's' : ''} but none are active.
            </p>
            <Link href="/budget">
              <Button variant="outline" size="sm" className="w-full">
                Manage Budgets
              </Button>
            </Link>
          </div>
        ) : (
          <div className="text-center py-4">
            <Sparkles className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground mb-3">
              No budget set up yet
            </p>
            <Link href="/budget">
              <Button size="sm" className="gap-2">
                <Sparkles className="h-3 w-3" />
                Create Smart Budget
              </Button>
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
