'use client'

import Link from 'next/link'
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react'
import { useCompleteNetWorth } from '@/hooks/useNetWorth'
import { useAnalyticsDashboard } from '@/hooks/useAnalytics'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'
import { cn } from '@/lib/utils'

export function DashboardHeader() {
  const { data: netWorth, isLoading: loadingNetWorth } = useCompleteNetWorth()
  const { data: analytics, isLoading: loadingAnalytics } = useAnalyticsDashboard()

  const netWorthValue = netWorth?.net_worth ?? 0
  const monthlyIncome = analytics?.income ?? 0
  const monthlySpending = analytics?.spending ?? 0
  const cashflow = monthlyIncome - monthlySpending
  const savingsRate = monthlyIncome > 0 ? ((cashflow / monthlyIncome) * 100) : 0

  if (loadingNetWorth || loadingAnalytics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <CardSkeleton className="h-24" />
        <CardSkeleton className="h-24" />
        <CardSkeleton className="h-24" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Net Worth - Clickable */}
      <Link
        href="/networth"
        className="group p-4 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg border border-primary/20 hover:border-primary/40 transition-all"
      >
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm text-muted-foreground">Net Worth</span>
          <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className={cn(
            "text-2xl font-bold",
            netWorthValue >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
          )}>
            <AnimatedCurrency value={netWorthValue} />
          </span>
          {netWorthValue >= 0 ? (
            <TrendingUp className="h-4 w-4 text-green-600" />
          ) : (
            <TrendingDown className="h-4 w-4 text-red-600" />
          )}
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          Assets: {formatCompact(netWorth?.total_assets ?? 0)} | Debt: {formatCompact(netWorth?.total_liabilities ?? 0)}
        </div>
      </Link>

      {/* This Month Cashflow */}
      <div className="p-4 bg-card rounded-lg border">
        <div className="text-sm text-muted-foreground mb-1">This Month</div>
        <div className="flex items-baseline gap-2">
          <span className={cn(
            "text-2xl font-bold",
            cashflow >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
          )}>
            <AnimatedCurrency value={cashflow} showSign />
          </span>
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          In: {formatCompact(monthlyIncome)} | Out: {formatCompact(monthlySpending)}
        </div>
      </div>

      {/* Savings Rate */}
      <div className="p-4 bg-card rounded-lg border">
        <div className="text-sm text-muted-foreground mb-1">Savings Rate</div>
        <div className="flex items-baseline gap-2">
          <span className={cn(
            "text-2xl font-bold",
            savingsRate >= 20 ? "text-green-600 dark:text-green-400" :
            savingsRate >= 10 ? "text-yellow-600 dark:text-yellow-400" :
            "text-red-600 dark:text-red-400"
          )}>
            {savingsRate.toFixed(0)}%
          </span>
          {savingsRate >= 20 ? (
            <TrendingUp className="h-4 w-4 text-green-600" />
          ) : savingsRate < 0 ? (
            <TrendingDown className="h-4 w-4 text-red-600" />
          ) : null}
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          {savingsRate >= 20 ? 'Great! Above 20% target' :
           savingsRate >= 10 ? 'Good, aim for 20%' :
           savingsRate >= 0 ? 'Try to save more' :
           'Spending more than earning'}
        </div>
      </div>
    </div>
  )
}

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`
  }
  return `$${value.toFixed(0)}`
}
