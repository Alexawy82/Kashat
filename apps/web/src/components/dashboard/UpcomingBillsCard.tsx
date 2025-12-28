'use client'

import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CalendarDays, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { cn } from '@/lib/utils'

interface UpcomingBill {
  id: string
  name: string
  amount: number
  due_date: string
  days_until: number
  is_essential: boolean
}

interface BillSummary {
  next_7_days: number
  next_30_days: number
  bill_count_7: number
  bill_count_30: number
}

function useUpcomingBills() {
  return useQuery({
    queryKey: ['calendar', 'upcoming', 7],
    queryFn: async () => {
      const { data, error } = await client.get<UpcomingBill[]>('/api/calendar/upcoming', {
        params: { query: { days: 7 } }
      })
      if (error) throw error
      return data || []
    },
    staleTime: 60_000,
  })
}

function useBillSummary() {
  return useQuery({
    queryKey: ['calendar', 'summary'],
    queryFn: async () => {
      const { data, error } = await client.get<BillSummary>('/api/calendar/summary')
      if (error) throw error
      return data
    },
    staleTime: 60_000,
  })
}

export function UpcomingBillsCard() {
  const { data: bills, isLoading: billsLoading } = useUpcomingBills()
  const { data: summary, isLoading: summaryLoading } = useBillSummary()

  const isLoading = billsLoading || summaryLoading

  if (isLoading) return <Card className="h-48 animate-pulse bg-muted/50" />

  const hasBills = bills && bills.length > 0
  const todayBills = bills?.filter(b => b.days_until === 0) || []
  const hasDueToday = todayBills.length > 0

  return (
    <Link href="/calendar">
      <Card className={cn(
        "hover:bg-accent/50 transition-colors cursor-pointer",
        hasDueToday && "border-amber-300 bg-amber-50"
      )}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Upcoming Bills</CardTitle>
          {hasDueToday ? (
            <AlertCircle className="h-4 w-4 text-amber-500" />
          ) : (
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
          )}
        </CardHeader>
        <CardContent>
          {hasDueToday && (
            <div className="mb-3 p-2 bg-amber-100 rounded text-xs text-amber-800">
              {todayBills.length} bill{todayBills.length > 1 ? 's' : ''} due today
            </div>
          )}

          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-2xl font-bold tracking-tighter">
              ${summary?.next_7_days?.toFixed(2) || '0.00'}
            </span>
            <span className="text-xs text-muted-foreground">
              next 7 days
            </span>
          </div>

          {hasBills ? (
            <div className="space-y-1">
              {bills.slice(0, 3).map((bill) => (
                <div
                  key={bill.id}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="truncate max-w-[60%]">
                    {bill.name}
                    {bill.days_until === 0 && (
                      <span className="ml-1 text-amber-600">(today)</span>
                    )}
                    {bill.days_until === 1 && (
                      <span className="ml-1 text-muted-foreground">(tomorrow)</span>
                    )}
                  </span>
                  <span className="font-medium">${bill.amount.toFixed(2)}</span>
                </div>
              ))}
              {bills.length > 3 && (
                <div className="text-xs text-muted-foreground text-center">
                  +{bills.length - 3} more this week
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No bills due this week
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  )
}
