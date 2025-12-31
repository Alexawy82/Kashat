'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Minus, Wallet, Calendar, ArrowRight } from 'lucide-react'
import { useIncomeSummary } from '@/hooks/useAnalytics'
import { cn } from '@/lib/utils'
import Link from 'next/link'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function formatMonth(monthStr: string): string {
  const [year, month] = monthStr.split('-')
  const date = new Date(parseInt(year), parseInt(month) - 1)
  return date.toLocaleDateString('en-US', { month: 'short' })
}

function getNextPayday(): string {
  // Estimate next payday (15th or last day of month)
  const today = new Date()
  const day = today.getDate()
  const month = today.getMonth()
  const year = today.getFullYear()

  let nextPay: Date
  if (day < 15) {
    nextPay = new Date(year, month, 15)
  } else {
    // Last day of month or first of next
    nextPay = new Date(year, month + 1, 0) // Last day of current month
    if (day >= nextPay.getDate() - 2) {
      nextPay = new Date(year, month + 1, 15) // 15th of next month
    }
  }

  const daysUntil = Math.ceil((nextPay.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  if (daysUntil === 0) return 'Today'
  if (daysUntil === 1) return 'Tomorrow'
  return `in ${daysUntil} days`
}

export function IncomeCard() {
  const { data, isLoading } = useIncomeSummary(6)

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wallet className="h-4 w-4 text-green-600" />
            Income
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data || data.monthly_trend.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wallet className="h-4 w-4 text-green-600" />
            Income
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No income data yet</p>
        </CardContent>
      </Card>
    )
  }

  const { current_month, average_monthly, by_source, monthly_trend } = data

  // Use last month if current month is $0
  const lastMonthData = monthly_trend[monthly_trend.length - 1]
  const prevMonthData = monthly_trend.length > 1 ? monthly_trend[monthly_trend.length - 2] : null

  const displayAmount = current_month.total > 0 ? current_month.total : lastMonthData?.total || 0
  const displayLabel = current_month.total > 0 ? 'This month' : 'Last month'

  // Calculate month-over-month change using actual data
  const changePercent = prevMonthData && lastMonthData
    ? ((lastMonthData.total - prevMonthData.total) / prevMonthData.total * 100)
    : 0

  const isUp = changePercent > 1
  const isDown = changePercent < -1
  const isStable = !isUp && !isDown

  // Get primary income source
  const primarySource = by_source[0]

  // Mini sparkline data (last 6 months)
  const maxTotal = Math.max(...monthly_trend.map(m => m.total), 1)

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Wallet className="h-4 w-4 text-green-600" />
            Income
          </CardTitle>
          <Link
            href="/transactions?filter=income"
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Primary Amount */}
        <div>
          <div className="text-2xl font-bold text-green-600">
            {formatCurrency(displayAmount)}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-muted-foreground">{displayLabel}</span>
            {!isStable && (
              <span className={cn(
                "text-xs flex items-center gap-0.5",
                isUp ? "text-green-600" : "text-amber-600"
              )}>
                {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {Math.abs(changePercent).toFixed(0)}%
              </span>
            )}
            {isStable && (
              <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                <Minus className="h-3 w-3" /> Stable
              </span>
            )}
          </div>
        </div>

        {/* Sparkline */}
        <div className="flex items-end gap-1 h-10">
          {monthly_trend.map((month, i) => (
            <div
              key={month.month}
              className={cn(
                "flex-1 rounded-sm transition-all",
                i === monthly_trend.length - 1 ? "bg-green-500" : "bg-green-200"
              )}
              style={{
                height: `${Math.max((month.total / maxTotal) * 100, 8)}%`,
              }}
              title={`${formatMonth(month.month)}: ${formatCurrency(month.total)}`}
            />
          ))}
        </div>

        {/* Key Stats */}
        <div className="grid grid-cols-2 gap-3 pt-2 border-t text-sm">
          <div>
            <p className="text-muted-foreground text-xs">Avg/month</p>
            <p className="font-medium">{formatCurrency(average_monthly)}</p>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Next payday</p>
            <p className="font-medium flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {getNextPayday()}
            </p>
          </div>
        </div>

        {/* Primary Source */}
        {primarySource && (
          <div className="pt-2 border-t">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground truncate max-w-[150px]">
                {primarySource.source}
              </span>
              <span className="font-medium">
                ~{formatCurrency(primarySource.avg_amount)}/pay
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
