'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
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
import {
  Plus,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  PiggyBank,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface BudgetCategory {
  id: string
  category_id: string
  category_name: string
  amount_limit: number
  rollover: boolean
  spent: number
  remaining: number
  percent_used: number
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
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Budget
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Budget</DialogTitle>
          <DialogDescription>
            Create a monthly budget to track your spending.
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

function BudgetCard({ budget }: { budget: Budget }) {
  const { data: progress } = useBudgetProgress(budget.id)

  const percentUsed = progress?.percent_used || 0
  const isOverBudget = percentUsed > 100
  const isWarning = percentUsed > 80 && percentUsed <= 100

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-base">{budget.name}</CardTitle>
          <CardDescription className="text-xs">
            {budget.period} budget
            {progress?.days_remaining !== undefined && (
              <> &bull; {progress.days_remaining} days left</>
            )}
          </CardDescription>
        </div>
        {progress && (
          <Badge
            variant={progress.on_track ? 'default' : 'destructive'}
            className={cn(
              progress.on_track && 'bg-green-100 text-green-800 hover:bg-green-100'
            )}
          >
            {progress.on_track ? (
              <>
                <CheckCircle className="mr-1 h-3 w-3" />
                On Track
              </>
            ) : (
              <>
                <AlertTriangle className="mr-1 h-3 w-3" />
                Over Budget
              </>
            )}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
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

        {/* Category Breakdown */}
        {progress?.categories && progress.categories.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Categories</div>
            {progress.categories.slice(0, 5).map((cat) => (
              <div key={cat.id} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="truncate max-w-[60%]">{cat.category_name}</span>
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

export default function BudgetPage() {
  const { data: budgets, isLoading, refetch } = useBudgets()

  // Calculate totals across all budgets
  const totalBudget = budgets?.reduce((sum, b) => sum + (b.total_limit || 0), 0) || 0
  const totalSpent = budgets?.reduce((sum, b) => sum + (b.total_spent || 0), 0) || 0
  const totalRemaining = totalBudget - totalSpent

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Budget</h1>
          <p className="text-muted-foreground">Track and manage your spending limits.</p>
        </div>
        <CreateBudgetDialog onCreated={() => refetch()} />
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
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

      {/* Budgets Grid */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading budgets...
        </div>
      ) : budgets && budgets.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {budgets.map((budget) => (
            <BudgetCard key={budget.id} budget={budget} />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <PiggyBank className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">No budgets yet</h3>
            <p className="text-sm text-muted-foreground text-center max-w-sm mt-1">
              Create your first budget to start tracking your spending against limits.
            </p>
            <CreateBudgetDialog onCreated={() => refetch()} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
