'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DollarSign, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useAnalyticsSummary } from '@/hooks/useAnalytics'
import { AnimatedCurrency, AnimatedPercentage } from '@/components/ui/AnimatedNumber'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'

export function CashflowSummaryCard() {
  const { data, isLoading, isError } = useAnalyticsSummary()

  if (isLoading) return <CardSkeleton className="h-40" />
  if (isError) return <Card className="h-40 bg-destructive/10 border-destructive/20 dark:bg-destructive/20 flex items-center justify-center text-destructive text-sm">Error loading cashflow</Card>

  const totals = data?.totals || {}
  const income = totals.income || 0
  const spend = Math.abs(totals.spend || 0)
  const net = totals.net || 0
  const savingsRate = income > 0 ? ((income - spend) / income * 100) : 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Cashflow Summary</CardTitle>
        <DollarSign className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" aria-hidden="true" /> Income
            </span>
            <span className="text-sm font-medium text-green-600 dark:text-green-400">
              ${income.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingDown className="h-3 w-3 text-red-500" aria-hidden="true" /> Spending
            </span>
            <span className="text-sm font-medium text-red-600 dark:text-red-400">
              ${spend.toLocaleString()}
            </span>
          </div>
          <div className="border-t pt-2 flex justify-between items-center">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Minus className="h-3 w-3" aria-hidden="true" /> Net
            </span>
            <AnimatedCurrency
              value={net}
              showSign
              className="text-lg font-bold"
              duration={600}
            />
          </div>
        </div>

        <div className="mt-3 pt-2 border-t">
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground">Savings Rate</span>
            <AnimatedPercentage
              value={savingsRate}
              duration={600}
              className={`text-sm font-semibold ${
                savingsRate >= 20
                  ? 'text-green-600 dark:text-green-400'
                  : savingsRate >= 10
                    ? 'text-yellow-600 dark:text-yellow-400'
                    : 'text-red-600 dark:text-red-400'
              }`}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
