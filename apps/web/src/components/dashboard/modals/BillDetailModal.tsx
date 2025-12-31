'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Calendar,
  DollarSign,
  Clock,
  Check,
  Edit,
  Loader2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react'
import { format, differenceInDays, addDays } from 'date-fns'
import { cn } from '@/lib/utils'
import { toast } from '@/components/ui/Toaster'

interface Bill {
  id: string
  name: string
  amount: number
  due_date: string
  recurring_type?: string
  cadence?: string
  is_essential?: boolean
  account_name?: string
  last_paid?: string
}

interface BillDetailModalProps {
  bill: Bill | null
  open: boolean
  onClose: () => void
  onMarkPaid: () => Promise<void>
  onEdit: () => void
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

export function BillDetailModal({
  bill,
  open,
  onClose,
  onMarkPaid,
  onEdit,
}: BillDetailModalProps) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  if (!bill) return null

  const dueDate = new Date(bill.due_date)
  const daysUntil = differenceInDays(dueDate, new Date())
  const isOverdue = daysUntil < 0
  const isDueToday = daysUntil === 0
  const isDueSoon = daysUntil <= 3 && daysUntil > 0

  const handleMarkPaid = async () => {
    setLoading(true)
    try {
      await onMarkPaid()
      toast.success(`${bill.name} marked as paid`)
      onClose()
    } catch (error) {
      toast.error('Failed to mark as paid')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {bill.name}
            {bill.is_essential && (
              <Badge variant="secondary" className="text-xs">Essential</Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Status Banner */}
          {isOverdue && (
            <div className="p-3 rounded-lg bg-red-100 dark:bg-red-950/30 text-red-700 dark:text-red-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm font-medium">
                Overdue by {Math.abs(daysUntil)} day{Math.abs(daysUntil) !== 1 ? 's' : ''}
              </span>
            </div>
          )}
          {isDueToday && (
            <div className="p-3 rounded-lg bg-amber-100 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span className="text-sm font-medium">Due today!</span>
            </div>
          )}
          {isDueSoon && (
            <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              <span className="text-sm font-medium">Due in {daysUntil} day{daysUntil !== 1 ? 's' : ''}</span>
            </div>
          )}

          {/* Details */}
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <DollarSign className="h-4 w-4" />
                <span className="text-sm">Amount</span>
              </div>
              <span className="font-bold text-lg">{formatCurrency(bill.amount)}</span>
            </div>

            <Separator />

            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span className="text-sm">Due Date</span>
              </div>
              <span className={cn(
                "font-medium",
                isOverdue && "text-red-600",
                isDueToday && "text-amber-600"
              )}>
                {format(dueDate, 'MMMM d, yyyy')}
              </span>
            </div>

            <Separator />

            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <RefreshCw className="h-4 w-4" />
                <span className="text-sm">Frequency</span>
              </div>
              <span className="font-medium capitalize">
                {bill.cadence || 'Monthly'}
              </span>
            </div>

            {bill.recurring_type && (
              <>
                <Separator />
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-muted-foreground">Type</span>
                  <Badge variant="outline" className="capitalize">
                    {bill.recurring_type.replace(/_/g, ' ')}
                  </Badge>
                </div>
              </>
            )}

            {bill.account_name && (
              <>
                <Separator />
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-muted-foreground">Account</span>
                  <span className="font-medium">{bill.account_name}</span>
                </div>
              </>
            )}

            {bill.last_paid && (
              <>
                <Separator />
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-muted-foreground">Last Paid</span>
                  <span className="text-sm">{format(new Date(bill.last_paid), 'MMM d, yyyy')}</span>
                </div>
              </>
            )}
          </div>
        </div>

        <DialogFooter className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onEdit}>
            <Edit className="h-4 w-4 mr-1" /> Edit
          </Button>
          <Button
            onClick={handleMarkPaid}
            disabled={loading}
            className={cn(
              isOverdue && "bg-red-600 hover:bg-red-700"
            )}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Check className="h-4 w-4 mr-1" />
            )}
            Mark as Paid
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
