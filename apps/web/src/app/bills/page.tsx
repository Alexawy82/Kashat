'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import Link from 'next/link'
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Clock,
  DollarSign,
  CheckCircle2,
  List,
  ArrowRight,
  XCircle,
  TrendingDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { PageHeader } from '@/components/ui/page-header'
import { SeriesDetailSheet } from '@/app/subscriptions/components/SeriesDetailSheet'

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

interface CancelledItem {
  id: string
  name: string
  amount: number
  cadence: string
  type?: string
  last_date?: string
  monthly_equivalent: number
}

interface CancelledStats {
  recent: CancelledItem[]
  total_count: number
  monthly_savings: number
  annual_savings: number
}

interface EnrichedCalendarData {
  calendar: MonthCalendar
  summary: BillSummary
  upcoming: UpcomingBill[]
  stats: {
    essential_count: number
    discretionary_count: number
    essential_total: number
    discretionary_total: number
  }
  cancelled?: CancelledStats
}

// Single enriched hook replaces 4 separate hooks
function useEnrichedCalendar(year: number, month: number) {
  return useQuery({
    queryKey: ['calendar', 'enriched', year, month],
    queryFn: async () => {
      const { data, error } = await client.get<EnrichedCalendarData>(
        `/api/calendar/month/${year}/${month}/enriched`
      )
      if (error) throw error
      return data
    },
  })
}

// Mark bill as paid mutation
function useMarkPaid() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (seriesId: string) => {
      const { error } = await client.post(`/api/recurring/${seriesId}/mark-paid`)
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function BillsPage() {
  const today = new Date()
  const [currentYear, setCurrentYear] = useState(today.getFullYear())
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1)
  const [showEssentialOnly, setShowEssentialOnly] = useState(false)
  const [selectedBill, setSelectedBill] = useState<UpcomingBill | null>(null)

  const { data, isLoading } = useEnrichedCalendar(currentYear, currentMonth)
  const markPaid = useMarkPaid()

  // Extract data from enriched response
  const calendar = data?.calendar
  const summary = data?.summary
  const upcomingBills = data?.upcoming || []
  const stats = data?.stats
  const cancelled = data?.cancelled

  // Filter calendar days based on essential filter
  const filteredDays = calendar?.days?.map(day => ({
    ...day,
    bills: showEssentialOnly
      ? day.bills.filter(b => b.is_essential)
      : day.bills,
    total_amount: showEssentialOnly
      ? day.bills.filter(b => b.is_essential).reduce((sum, b) => sum + b.amount, 0)
      : day.total_amount
  }))

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
  const firstDayOfMonth = filteredDays?.[0]?.date
    ? new Date(filteredDays[0].date).getDay()
    : 0

  // Convert bill to series format for detail sheet
  const billToSeries = (bill: UpcomingBill) => ({
    id: bill.id,
    series_id: bill.id,
    name: bill.name,
    merchant: bill.name,
    amount: bill.amount,
    amount_mean: bill.amount,
    recurring_type: bill.recurring_type,
    cadence: bill.cadence,
    is_essential: bill.is_essential,
    next_date: bill.due_date,
    account_name: bill.account_name,
  })

  const handleMarkPaid = (e: React.MouseEvent, billId: string) => {
    e.stopPropagation()
    markPaid.mutate(billId)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bills"
        description="Track your upcoming payments and bills."
        helpItems={[
          "View all upcoming bills on the calendar",
          "Click any bill to see details or mark it as paid",
          "Days with bills are highlighted in amber; today is highlighted in blue",
          "Essential bills (rent, utilities) show in red for priority",
          "Toggle 'Essential only' to focus on must-pay bills",
          "See next 7, 30, and 90 day spending forecasts in the summary cards"
        ]}
      />

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

      {/* Cancelled Subscriptions Widget */}
      {cancelled && cancelled.total_count > 0 && (
        <Card className="border-green-200 bg-green-50/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-green-600" />
              <CardTitle className="text-base font-semibold text-green-800">Savings from Cancelled Bills</CardTitle>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-green-600">
                ${cancelled.monthly_savings.toFixed(2)}<span className="text-sm font-normal text-green-600/70">/mo</span>
              </div>
              <p className="text-xs text-green-600/70">
                ${cancelled.annual_savings.toFixed(2)}/year
              </p>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {cancelled.recent.slice(0, 6).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-100 text-green-800 text-xs"
                >
                  <XCircle className="h-3 w-3" />
                  <span className="font-medium">{item.name}</span>
                  <span className="text-green-600">${item.monthly_equivalent.toFixed(0)}/mo</span>
                </div>
              ))}
              {cancelled.total_count > 6 && (
                <div className="px-2 py-1 rounded-full bg-green-100 text-green-700 text-xs">
                  +{cancelled.total_count - 6} more
                </div>
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
                {showEssentialOnly ? (
                  <span>{stats?.essential_count || 0} essential bills totaling ${stats?.essential_total?.toFixed(2) || '0.00'}</span>
                ) : (
                  <span>{calendar?.total_bills || 0} bills totaling ${calendar?.total_amount?.toFixed(2) || '0.00'}</span>
                )}
              </CardDescription>
            </div>
            <div className="flex items-center gap-4">
              {/* Essential Filter Toggle */}
              <div className="flex items-center gap-2">
                <Switch
                  id="essential-only"
                  checked={showEssentialOnly}
                  onCheckedChange={setShowEssentialOnly}
                />
                <Label htmlFor="essential-only" className="text-sm">Essential only</Label>
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
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
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
                {filteredDays?.map((day) => {
                  const isToday = day.date === today.toISOString().split('T')[0]
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
                              onClick={() => setSelectedBill(bill)}
                              className={cn(
                                "text-xs px-1 py-0.5 rounded truncate cursor-pointer",
                                "hover:ring-2 hover:ring-blue-400 transition-shadow",
                                bill.is_essential
                                  ? "bg-red-100 text-red-800"
                                  : "bg-amber-100 text-amber-800"
                              )}
                              title={`${bill.name}: $${bill.amount.toFixed(2)} - Click for details`}
                            >
                              ${bill.amount.toFixed(0)} {bill.name}
                            </div>
                          ))}
                          {day.bills.length > 2 && (
                            <div
                              className="text-xs text-muted-foreground px-1 cursor-pointer hover:text-foreground"
                              onClick={() => setSelectedBill(day.bills[2])}
                            >
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
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Due This Week</CardTitle>
            <Link href="/subscriptions">
              <Button variant="ghost" size="sm" className="text-xs gap-1">
                <List className="h-3 w-3" />
                Manage
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {upcomingBills && upcomingBills.length > 0 ? (
              upcomingBills.map((bill) => (
                <div
                  key={bill.id}
                  onClick={() => setSelectedBill(bill)}
                  className="flex items-center justify-between p-2 rounded border cursor-pointer hover:bg-accent transition-colors"
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
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold">
                      ${bill.amount.toFixed(2)}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 hover:bg-green-100"
                      onClick={(e) => handleMarkPaid(e, bill.id)}
                      disabled={markPaid.isPending}
                      title="Mark as paid"
                    >
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground text-center py-4">
                No bills due this week
              </div>
            )}

            {/* Link to Subscriptions */}
            <div className="pt-2 border-t">
              <Link href="/subscriptions">
                <Button variant="outline" className="w-full gap-2">
                  Manage All Recurring
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bill Detail Sheet */}
      <SeriesDetailSheet
        open={!!selectedBill}
        onOpenChange={(open) => !open && setSelectedBill(null)}
        series={selectedBill ? billToSeries(selectedBill) : null}
      />
    </div>
  )
}
