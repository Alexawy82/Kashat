'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  AlertCircle,
  Clock,
  DollarSign,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface UpcomingBill {
  id: string
  name: string
  amount: number
  due_date: string
  recurring_type?: string
  cadence?: string
  is_essential: boolean
  days_until: number
  account_name?: string
}

interface CalendarDay {
  date: string
  day: number
  bills: UpcomingBill[]
  total_amount: number
}

interface MonthCalendar {
  year: number
  month: number
  month_name: string
  days: CalendarDay[]
  total_bills: number
  total_amount: number
}

interface BillSummary {
  next_7_days: number
  next_30_days: number
  next_90_days: number
  bill_count_7: number
  bill_count_30: number
  bill_count_90: number
}

function useCalendarMonth(year: number, month: number) {
  return useQuery({
    queryKey: ['calendar', 'month', year, month],
    queryFn: async () => {
      const { data, error } = await client.get<MonthCalendar>(`/api/calendar/month/${year}/${month}`)
      if (error) throw error
      return data
    },
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
  })
}

function useUpcomingBills(days: number = 7) {
  return useQuery({
    queryKey: ['calendar', 'upcoming', days],
    queryFn: async () => {
      const { data, error } = await client.get<UpcomingBill[]>(`/api/calendar/upcoming`, {
        params: { query: { days } }
      })
      if (error) throw error
      return data || []
    },
  })
}

function useOverdueBills() {
  return useQuery({
    queryKey: ['calendar', 'overdue'],
    queryFn: async () => {
      const { data, error } = await client.get<UpcomingBill[]>('/api/calendar/overdue')
      if (error) throw error
      return data || []
    },
  })
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function BillsPage() {
  const today = new Date()
  const [currentYear, setCurrentYear] = useState(today.getFullYear())
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1)

  const { data: calendar, isLoading: calendarLoading } = useCalendarMonth(currentYear, currentMonth)
  const { data: summary } = useBillSummary()
  const { data: upcomingBills } = useUpcomingBills(7)
  const { data: overdueBills } = useOverdueBills()

  const goToPrevMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12)
      setCurrentYear(currentYear - 1)
    } else {
      setCurrentMonth(currentMonth - 1)
    }
  }

  const goToNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1)
      setCurrentYear(currentYear + 1)
    } else {
      setCurrentMonth(currentMonth + 1)
    }
  }

  const goToToday = () => {
    setCurrentYear(today.getFullYear())
    setCurrentMonth(today.getMonth() + 1)
  }

  // Calculate first day offset for calendar grid
  const firstDayOfMonth = calendar?.days?.[0]?.date
    ? new Date(calendar.days[0].date).getDay()
    : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Bills</h1>
          <p className="text-muted-foreground">Track your upcoming payments and bills.</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Next 7 Days</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${summary?.next_7_days?.toFixed(2) || '0.00'}</div>
            <p className="text-xs text-muted-foreground">
              {summary?.bill_count_7 || 0} bills due
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Next 30 Days</CardTitle>
            <CalendarIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${summary?.next_30_days?.toFixed(2) || '0.00'}</div>
            <p className="text-xs text-muted-foreground">
              {summary?.bill_count_30 || 0} bills due
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Next 90 Days</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${summary?.next_90_days?.toFixed(2) || '0.00'}</div>
            <p className="text-xs text-muted-foreground">
              {summary?.bill_count_90 || 0} bills due
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Overdue Alert */}
      {overdueBills && overdueBills.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              Overdue Bills ({overdueBills.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {overdueBills.slice(0, 5).map((bill) => (
                <Badge key={bill.id} variant="destructive">
                  {bill.name} - ${bill.amount.toFixed(2)}
                </Badge>
              ))}
              {overdueBills.length > 5 && (
                <Badge variant="outline">+{overdueBills.length - 5} more</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Calendar */}
        <Card className="lg:col-span-3">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>{calendar?.month_name || 'Loading...'} {currentYear}</CardTitle>
              <CardDescription>
                {calendar?.total_bills || 0} bills totaling ${calendar?.total_amount?.toFixed(2) || '0.00'}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={goToToday}>
                Today
              </Button>
              <Button variant="outline" size="icon" onClick={goToPrevMonth}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={goToNextMonth}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {calendarLoading ? (
              <div className="h-96 flex items-center justify-center text-muted-foreground">
                Loading calendar...
              </div>
            ) : (
              <div className="grid grid-cols-7 gap-1">
                {/* Weekday headers */}
                {WEEKDAYS.map((day) => (
                  <div
                    key={day}
                    className="text-center text-sm font-medium text-muted-foreground py-2"
                  >
                    {day}
                  </div>
                ))}

                {/* Empty cells for offset */}
                {Array.from({ length: firstDayOfMonth }).map((_, i) => (
                  <div key={`empty-${i}`} className="h-24 bg-muted/30 rounded" />
                ))}

                {/* Calendar days */}
                {calendar?.days?.map((day) => {
                  const isToday =
                    day.date === today.toISOString().split('T')[0]
                  const hasBills = day.bills.length > 0

                  return (
                    <div
                      key={day.date}
                      className={cn(
                        "h-24 rounded border p-1 overflow-hidden",
                        isToday && "border-blue-500 bg-blue-50",
                        hasBills && !isToday && "bg-amber-50 border-amber-200"
                      )}
                    >
                      <div className={cn(
                        "text-sm font-medium mb-1",
                        isToday && "text-blue-600"
                      )}>
                        {day.day}
                      </div>
                      {hasBills && (
                        <div className="space-y-0.5">
                          {day.bills.slice(0, 2).map((bill) => (
                            <div
                              key={bill.id}
                              className={cn(
                                "text-xs px-1 py-0.5 rounded truncate",
                                bill.is_essential
                                  ? "bg-red-100 text-red-800"
                                  : "bg-amber-100 text-amber-800"
                              )}
                              title={`${bill.name}: $${bill.amount.toFixed(2)}`}
                            >
                              ${bill.amount.toFixed(0)} {bill.name}
                            </div>
                          ))}
                          {day.bills.length > 2 && (
                            <div className="text-xs text-muted-foreground px-1">
                              +{day.bills.length - 2} more
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Upcoming Bills Sidebar */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Due This Week</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {upcomingBills && upcomingBills.length > 0 ? (
              upcomingBills.map((bill) => (
                <div
                  key={bill.id}
                  className="flex items-center justify-between p-2 rounded border"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-sm truncate">{bill.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {bill.days_until === 0
                        ? 'Due today'
                        : bill.days_until === 1
                        ? 'Due tomorrow'
                        : `Due in ${bill.days_until} days`}
                    </div>
                  </div>
                  <div className="text-sm font-semibold">
                    ${bill.amount.toFixed(2)}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground text-center py-4">
                No bills due this week
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
