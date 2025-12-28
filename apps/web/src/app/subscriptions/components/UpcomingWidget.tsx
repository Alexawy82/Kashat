'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CalendarClock, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { formatAmount } from '@/app/subscriptions/lib/recurringUtils'

type UpcomingItem = {
  series_id?: string
  merchant?: string
  amount?: number
  date?: string
  cadence?: string
  type?: string
  is_essential?: boolean
}

function formatDateLabel(dateStr: string): string {
  try {
    const date = new Date(dateStr + 'T00:00:00')
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)

    if (date.toDateString() === today.toDateString()) {
      return 'Today'
    }
    if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow'
    }

    const options: Intl.DateTimeFormatOptions = { weekday: 'short', month: 'short', day: 'numeric' }
    return date.toLocaleDateString('en-US', options)
  } catch {
    return dateStr
  }
}

function groupByDate(items: UpcomingItem[]) {
  return items.reduce<Record<string, UpcomingItem[]>>((acc, item) => {
    const key = item.date || 'Unknown'
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {})
}

export function UpcomingWidget({
  items,
  isLoading,
  onItemClick,
}: {
  items: UpcomingItem[]
  isLoading?: boolean
  onItemClick?: (item: UpcomingItem) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const groups = groupByDate(items)
  const allDates = Object.keys(groups)
  const dates = expanded ? allDates : allDates.slice(0, 5)
  const hasMore = allDates.length > 5

  // Calculate total for the period
  const totalAmount = items.reduce((sum, item) => sum + (item.amount || 0), 0)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CalendarClock className="h-5 w-5 text-blue-500" />
              Upcoming Payments
            </CardTitle>
            <CardDescription>Next 14 days of confirmed recurring charges.</CardDescription>
          </div>
          {items.length > 0 && (
            <div className="text-right">
              <div className="text-lg font-semibold">{formatAmount(totalAmount)}</div>
              <div className="text-xs text-muted-foreground">{items.length} payments</div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading upcoming payments…</div>
        ) : dates.length === 0 ? (
          <div className="text-sm text-muted-foreground py-4 text-center">
            No upcoming recurring payments found.
          </div>
        ) : (
          <>
            {dates.map((date) => (
              <div key={date} className="space-y-1.5">
                <div className="text-xs font-semibold text-muted-foreground">{formatDateLabel(date)}</div>
                <div className="space-y-1">
                  {groups[date].map((item) => (
                    <div
                      key={item.series_id || item.merchant}
                      className={`flex items-center justify-between p-2 rounded-lg ${
                        onItemClick ? 'hover:bg-muted/50 cursor-pointer transition-colors' : ''
                      }`}
                      onClick={() => onItemClick?.(item)}
                    >
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium">{item.merchant || 'Unknown'}</span>
                        {item.is_essential && (
                          <Badge variant="outline" className="text-[10px] border-blue-200 text-blue-700">
                            Essential
                          </Badge>
                        )}
                        {onItemClick && <ExternalLink className="h-3 w-3 text-muted-foreground" />}
                      </div>
                      <div className="text-sm font-medium">{formatAmount(item.amount || 0)}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {hasMore && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? (
                  <>
                    Show Less <ChevronUp className="ml-1 h-3 w-3" />
                  </>
                ) : (
                  <>
                    View All ({allDates.length - 5} more days) <ChevronDown className="ml-1 h-3 w-3" />
                  </>
                )}
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
