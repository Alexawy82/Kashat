'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CalendarClock, Sparkles, TrendingDown } from 'lucide-react'
import { useOptimizations, useRecurringSummary, useUpcomingPayments } from '@/hooks/useRecurring'
import { formatAmount } from '@/app/subscriptions/lib/recurringUtils'

export function RecurringSummaryWidget() {
  const { data: summary, isLoading } = useRecurringSummary()
  const { data: upcoming } = useUpcomingPayments(7)
  const { data: optimizations } = useOptimizations(2)

  const upcomingList = Array.isArray(upcoming) ? upcoming : (upcoming as any)?.items || []
  const optimizationsList = Array.isArray(optimizations) ? optimizations : (optimizations as any)?.suggestions || []

  return (
    <Card>
      <CardHeader className="flex items-start justify-between gap-2">
        <div>
          <CardTitle className="text-base">Recurring Overview</CardTitle>
          <CardDescription>Snapshot of upcoming and savings</CardDescription>
        </div>
        <Badge variant="outline" className="text-[10px]">7 days</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border bg-muted/30 p-3">
          <div className="text-xs text-muted-foreground">Monthly recurring</div>
          <div className="text-xl font-semibold">
            {isLoading ? '—' : formatAmount(summary?.total_monthly || 0)}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <CalendarClock className="h-4 w-4 text-blue-500" />
            Upcoming
          </div>
          {upcomingList.length === 0 ? (
            <p className="text-xs text-muted-foreground">No upcoming payments in the next week.</p>
          ) : (
            upcomingList.slice(0, 3).map((item: any) => (
              <div key={item.series_id || item.merchant} className="flex items-center justify-between text-sm">
                <span>{item.merchant || 'Unknown'}</span>
                <span className="font-medium">{formatAmount(item.amount || 0)}</span>
              </div>
            ))
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Sparkles className="h-4 w-4 text-amber-500" />
            Savings
          </div>
          {optimizationsList.length === 0 ? (
            <p className="text-xs text-muted-foreground">No savings suggestions yet.</p>
          ) : (
            optimizationsList.map((item: any) => (
              <div key={item.id} className="flex items-center justify-between text-sm">
                <span className="truncate">{item.title}</span>
                <span className="flex items-center gap-1 text-xs text-emerald-600">
                  <TrendingDown className="h-3 w-3" />
                  {formatAmount(item.potential_annual_savings || 0)}/yr
                </span>
              </div>
            ))
          )}
        </div>

        <Link href="/subscriptions">
          <Button variant="outline" size="sm" className="w-full">
            Open Subscriptions
          </Button>
        </Link>
      </CardContent>
    </Card>
  )
}
