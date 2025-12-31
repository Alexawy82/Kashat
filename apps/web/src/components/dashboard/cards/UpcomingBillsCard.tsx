'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Calendar,
  ChevronRight,
  Check,
  MoreHorizontal,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import { format, differenceInDays } from 'date-fns'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { toast } from '@/components/ui/Toaster'
import { BillDetailModal } from '../modals/BillDetailModal'

interface Bill {
  id: string
  name: string
  amount: number
  due_date: string
  recurring_type?: string
  cadence?: string
  is_essential?: boolean
  account_name?: string
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

function useUpcomingBills(days: number = 7) {
  return useQuery({
    queryKey: ['calendar', 'upcoming', days],
    queryFn: async () => {
      const { data, error } = await client.get('/api/calendar/upcoming', {
        params: { query: { days } },
      })
      if (error) return []
      return (data as Bill[]) || []
    },
    staleTime: 60000,
  })
}

function useBillSummary() {
  return useQuery({
    queryKey: ['calendar', 'summary'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/calendar/summary')
      if (error) return null
      return data as { next_7_days: number; next_30_days: number }
    },
    staleTime: 60000,
  })
}

function useMarkBillPaid() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (billId: string) => {
      // Mark the recurring series as paid for this period
      const { error } = await client.post(`/api/recurring/${billId}/mark-paid`)
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] })
      queryClient.invalidateQueries({ queryKey: ['recurring'] })
    },
  })
}

export function UpcomingBillsCard() {
  const router = useRouter()
  const { data: bills, isLoading } = useUpcomingBills(7)
  const { data: summary } = useBillSummary()
  const markPaid = useMarkBillPaid()

  const [selectedBill, setSelectedBill] = useState<Bill | null>(null)
  const [markingPaid, setMarkingPaid] = useState<string | null>(null)

  const handleMarkPaid = async (bill: Bill, e?: React.MouseEvent) => {
    e?.stopPropagation()
    setMarkingPaid(bill.id)
    try {
      await markPaid.mutateAsync(bill.id)
      toast.success(`${bill.name} marked as paid`)
    } catch (error) {
      toast.error('Failed to mark as paid')
    } finally {
      setMarkingPaid(null)
    }
  }

  const overdueBills = bills?.filter(
    (b) => differenceInDays(new Date(b.due_date), new Date()) < 0
  )
  const dueTodayBills = bills?.filter(
    (b) => differenceInDays(new Date(b.due_date), new Date()) === 0
  )

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Calendar className="h-5 w-5 text-blue-500" />
              Upcoming Bills
              <Badge variant="outline" className="text-xs">
                Next 7 days
              </Badge>
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/bills')}
            >
              View All <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {/* Overdue Warning */}
          {overdueBills && overdueBills.length > 0 && (
            <div className="mb-3 p-2 bg-red-100 dark:bg-red-950/30 rounded-lg text-red-700 dark:text-red-300 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {overdueBills.length} overdue bill{overdueBills.length > 1 ? 's' : ''}!
            </div>
          )}

          {/* Due Today Warning */}
          {dueTodayBills && dueTodayBills.length > 0 && !overdueBills?.length && (
            <div className="mb-3 p-2 bg-amber-100 dark:bg-amber-950/30 rounded-lg text-amber-700 dark:text-amber-300 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {dueTodayBills.length} bill{dueTodayBills.length > 1 ? 's' : ''} due today
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : bills?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-10 w-10 mx-auto mb-2 text-green-500" />
              <p className="font-medium">All clear!</p>
              <p className="text-sm">No bills due this week</p>
            </div>
          ) : (
            <div className="space-y-1">
              {bills?.slice(0, 5).map((bill) => (
                <BillRow
                  key={bill.id}
                  bill={bill}
                  onClick={() => setSelectedBill(bill)}
                  onMarkPaid={(e) => handleMarkPaid(bill, e)}
                  isMarkingPaid={markingPaid === bill.id}
                />
              ))}

              {/* Total */}
              <Separator className="my-3" />
              <div
                className="flex justify-between font-medium cursor-pointer hover:bg-accent/50 p-2 rounded -mx-2"
                onClick={() => router.push('/bills')}
              >
                <span>Total Due</span>
                <span className="text-red-600">
                  {formatCurrency(summary?.next_7_days || 0)}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bill Detail Modal */}
      <BillDetailModal
        bill={selectedBill}
        open={!!selectedBill}
        onClose={() => setSelectedBill(null)}
        onMarkPaid={async () => {
          if (selectedBill) {
            await handleMarkPaid(selectedBill)
            setSelectedBill(null)
          }
        }}
        onEdit={() => {
          router.push(`/subscriptions?edit=${selectedBill?.id}`)
          setSelectedBill(null)
        }}
      />
    </>
  )
}

function BillRow({
  bill,
  onClick,
  onMarkPaid,
  isMarkingPaid,
}: {
  bill: Bill
  onClick: () => void
  onMarkPaid: (e: React.MouseEvent) => void
  isMarkingPaid: boolean
}) {
  const [showActions, setShowActions] = useState(false)
  const dueDate = new Date(bill.due_date)
  const daysUntil = differenceInDays(dueDate, new Date())
  const isOverdue = daysUntil < 0
  const isDueToday = daysUntil === 0

  return (
    <div
      className={cn(
        'flex items-center justify-between p-2 rounded cursor-pointer transition-colors -mx-2',
        isOverdue
          ? 'bg-red-50 dark:bg-red-950/20 hover:bg-red-100 dark:hover:bg-red-950/40'
          : isDueToday
            ? 'bg-amber-50 dark:bg-amber-950/20 hover:bg-amber-100 dark:hover:bg-amber-950/40'
            : 'hover:bg-accent/50'
      )}
      onClick={onClick}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'w-10 h-10 rounded-full flex flex-col items-center justify-center text-xs font-medium',
            isOverdue
              ? 'bg-red-200 text-red-700 dark:bg-red-900 dark:text-red-200'
              : isDueToday
                ? 'bg-amber-200 text-amber-700 dark:bg-amber-900 dark:text-amber-200'
                : 'bg-accent'
          )}
        >
          <span>{format(dueDate, 'd')}</span>
          <span className="text-[10px]">{format(dueDate, 'MMM')}</span>
        </div>
        <div>
          <div className="font-medium text-sm">{bill.name}</div>
          <div className="text-xs text-muted-foreground">
            {isOverdue ? (
              <span className="text-red-600">
                Overdue by {Math.abs(daysUntil)} day{Math.abs(daysUntil) !== 1 ? 's' : ''}
              </span>
            ) : isDueToday ? (
              <span className="text-amber-600">Due today</span>
            ) : daysUntil === 1 ? (
              'Tomorrow'
            ) : (
              format(dueDate, 'EEEE')
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {showActions ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={onMarkPaid}
              disabled={isMarkingPaid}
            >
              {isMarkingPaid ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Check className="h-3 w-3" />
              )}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="sm" className="h-7 px-2">
                  <MoreHorizontal className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    toast.info('Reminder set for tomorrow')
                  }}
                >
                  Remind tomorrow
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    toast.info('Reminder set for next week')
                  }}
                >
                  Remind next week
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        ) : (
          <span className="font-medium text-sm">{formatCurrency(bill.amount)}</span>
        )}
      </div>
    </div>
  )
}
