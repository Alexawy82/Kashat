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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Calendar,
  DollarSign,
  Tag,
  Building2,
  CreditCard,
  Edit,
  Loader2,
  Trash2,
  Split,
  Check,
} from 'lucide-react'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import { toast } from '@/components/ui/Toaster'
import { useConfirm } from '@/components/ui/ConfirmDialog'
import { useCategories, useAssignCategory, useDeleteTransaction } from '@/hooks/useCategories'

interface Transaction {
  id: string
  date: string
  description: string
  merchant?: string
  amount: number
  category?: {
    id: string
    name: string
    color?: string
  }
  account?: {
    id: string
    name: string
  }
  is_income?: boolean
  is_transfer?: boolean
  notes?: string
}

interface TransactionDetailModalProps {
  transaction: Transaction | null
  open: boolean
  onClose: () => void
  onEdit?: () => void
  onSplit?: () => void
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(Math.abs(value))
}

export function TransactionDetailModal({
  transaction,
  open,
  onClose,
  onEdit,
  onSplit,
}: TransactionDetailModalProps) {
  const router = useRouter()
  const { data: categories } = useCategories()
  const assignCategory = useAssignCategory()
  const deleteTransaction = useDeleteTransaction()
  const { confirm, ConfirmDialog } = useConfirm()

  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(
    transaction?.category?.id
  )
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  if (!transaction) return null

  const isIncome = transaction.amount > 0 || transaction.is_income
  const isTransfer = transaction.is_transfer

  const handleCategoryChange = async (categoryId: string) => {
    setSelectedCategory(categoryId)
    setSaving(true)
    try {
      await assignCategory.mutateAsync({
        txId: transaction.id,
        categoryId,
      })
      toast.success('Category updated')
    } catch (error) {
      toast.error('Failed to update category')
      setSelectedCategory(transaction.category?.id)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    const confirmed = await confirm({
      title: 'Delete Transaction',
      description: 'Are you sure you want to delete this transaction? This cannot be undone.',
      confirmLabel: 'Delete',
      variant: 'destructive',
    })
    if (!confirmed) return

    setDeleting(true)
    try {
      await deleteTransaction.mutateAsync(transaction.id)
      toast.success('Transaction deleted')
      onClose()
    } catch (error) {
      toast.error('Failed to delete transaction')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Transaction Details
            {isIncome && <Badge className="bg-green-100 text-green-800">Income</Badge>}
            {isTransfer && <Badge variant="outline">Transfer</Badge>}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Amount */}
          <div className="text-center py-4">
            <span className={cn(
              "text-3xl font-bold",
              isIncome ? "text-green-600" : "text-red-600"
            )}>
              {isIncome ? '+' : '-'}{formatCurrency(transaction.amount)}
            </span>
          </div>

          <Separator />

          {/* Details */}
          <div className="space-y-3">
            {/* Merchant/Description */}
            <div className="flex items-start justify-between py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Building2 className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm">Merchant</span>
              </div>
              <span className="font-medium text-right max-w-[60%] truncate">
                {transaction.merchant || transaction.description}
              </span>
            </div>

            <Separator />

            {/* Date */}
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span className="text-sm">Date</span>
              </div>
              <span className="font-medium">
                {format(new Date(transaction.date), 'MMMM d, yyyy')}
              </span>
            </div>

            <Separator />

            {/* Category - Editable */}
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Tag className="h-4 w-4" />
                <span className="text-sm">Category</span>
              </div>
              <div className="flex items-center gap-2">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                <Select
                  value={selectedCategory}
                  onValueChange={handleCategoryChange}
                  disabled={saving}
                >
                  <SelectTrigger className="w-[160px] h-8">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories?.map((cat: { id: string; name: string; color?: string }) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: cat.color || '#888' }}
                          />
                          {cat.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Account */}
            {transaction.account && (
              <>
                <Separator />
                <div className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <CreditCard className="h-4 w-4" />
                    <span className="text-sm">Account</span>
                  </div>
                  <span className="font-medium">{transaction.account.name}</span>
                </div>
              </>
            )}

            {/* Notes */}
            {transaction.notes && (
              <>
                <Separator />
                <div className="py-2">
                  <span className="text-sm text-muted-foreground">Notes</span>
                  <p className="text-sm mt-1">{transaction.notes}</p>
                </div>
              </>
            )}
          </div>
        </div>

        <DialogFooter className="flex flex-wrap gap-2 mt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDelete}
            disabled={deleting}
            className="text-red-600 hover:text-red-700"
          >
            {deleting ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4 mr-1" />
            )}
            Delete
          </Button>
          {onSplit && (
            <Button variant="outline" size="sm" onClick={onSplit}>
              <Split className="h-4 w-4 mr-1" /> Split
            </Button>
          )}
          {onEdit && (
            <Button variant="outline" size="sm" onClick={onEdit}>
              <Edit className="h-4 w-4 mr-1" /> Edit
            </Button>
          )}
          <Button size="sm" onClick={onClose}>
            <Check className="h-4 w-4 mr-1" /> Done
          </Button>
        </DialogFooter>
      </DialogContent>
      <ConfirmDialog />
    </Dialog>
  )
}
