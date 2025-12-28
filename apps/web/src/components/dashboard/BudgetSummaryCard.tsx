'use client'

import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { PiggyBank, AlertTriangle, CheckCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { cn } from '@/lib/utils'

interface Budget {
  id: string
  name: string
  period: string
  total_limit: number
  total_spent: number
}

function useBudgets() {
  return useQuery({
    queryKey: ['budgets'],
    queryFn: async () => {
      const { data, error } = await client.get<Budget[]>('/api/budgets')
      if (error) throw error
      return data || []
    },
    staleTime: 60_000,
  })
}

export function BudgetSummaryCard() {
  const { data: budgets, isLoading, isError } = useBudgets()

  if (isLoading) return <Card className="h-40 animate-pulse bg-muted/50" />
  if (isError) return <Card className="h-40 bg-red-50 border-red-100 flex items-center justify-center text-red-500 text-sm">Error loading budget</Card>

  const totalLimit = budgets?.reduce((sum, b) => sum + (b.total_limit || 0), 0) || 0
  const totalSpent = budgets?.reduce((sum, b) => sum + (b.total_spent || 0), 0) || 0
  const percentUsed = totalLimit > 0 ? (totalSpent / totalLimit) * 100 : 0
  const isOverBudget = percentUsed > 100
  const isWarning = percentUsed > 80 && percentUsed <= 100

  if (!budgets || budgets.length === 0) {
    return (
      <Link href="/budget">
        <Card className="hover:bg-accent/50 transition-colors cursor-pointer h-40">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Budget</CardTitle>
            <PiggyBank className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center h-20">
            <p className="text-sm text-muted-foreground">No budget set up</p>
            <p className="text-xs text-blue-500 mt-1">Click to create one</p>
          </CardContent>
        </Card>
      </Link>
    )
  }

  return (
    <Link href="/budget">
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Budget</CardTitle>
          {isOverBudget ? (
            <AlertTriangle className="h-4 w-4 text-red-500" />
          ) : (
            <PiggyBank className="h-4 w-4 text-muted-foreground" />
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <span className={cn(
              "text-2xl font-bold tracking-tighter",
              isOverBudget ? "text-red-600" : isWarning ? "text-amber-600" : "text-green-600"
            )}>
              ${totalSpent.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>
            <span className="text-sm text-muted-foreground">
              / ${totalLimit.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>
          </div>
          <Progress
            value={Math.min(percentUsed, 100)}
            className={cn(
              "mt-2 h-2",
              isOverBudget && "[&>div]:bg-red-500",
              isWarning && "[&>div]:bg-amber-500"
            )}
          />
          <div className="flex items-center justify-between mt-2 text-xs">
            <span className="text-muted-foreground">{percentUsed.toFixed(0)}% used</span>
            {isOverBudget ? (
              <span className="text-red-500 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Over budget
              </span>
            ) : (
              <span className="text-green-500 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                On track
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
