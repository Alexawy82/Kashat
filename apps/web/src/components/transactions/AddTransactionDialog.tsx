'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Plus, Loader2, DollarSign, Calendar } from 'lucide-react'
import { useAccounts } from '@/hooks/useAccounts'
import { useCategories } from '@/hooks/useCategories'
import { useCreateTransaction } from '@/hooks/useTransactions'
import { toast } from '@/components/ui/Toaster'
import { format } from 'date-fns'

interface AddTransactionDialogProps {
  trigger?: React.ReactNode
  onSuccess?: () => void
}

export function AddTransactionDialog({ trigger, onSuccess }: AddTransactionDialogProps) {
  const [open, setOpen] = useState(false)
  const { data: accounts } = useAccounts()
  const { data: categories } = useCategories()
  const createTransaction = useCreateTransaction()

  const [formData, setFormData] = useState({
    account_id: '',
    posted_at: format(new Date(), 'yyyy-MM-dd'),
    amount: '',
    description: '',
    category_id: '',
    is_income: false,
    is_business: false,
  })

  const resetForm = () => {
    setFormData({
      account_id: '',
      posted_at: format(new Date(), 'yyyy-MM-dd'),
      amount: '',
      description: '',
      category_id: '',
      is_income: false,
      is_business: false,
    })
  }

  const handleSubmit = async () => {
    if (!formData.account_id) {
      toast.error('Please select an account')
      return
    }
    if (!formData.description.trim()) {
      toast.error('Please enter a description')
      return
    }
    if (!formData.amount || parseFloat(formData.amount) === 0) {
      toast.error('Please enter a valid amount')
      return
    }

    try {
      // Convert amount: negative for expenses, positive for income
      let amount = Math.abs(parseFloat(formData.amount))
      if (!formData.is_income) {
        amount = -amount
      }

      await createTransaction.mutateAsync({
        account_id: formData.account_id,
        posted_at: formData.posted_at,
        amount,
        description: formData.description,
        category_id: formData.category_id || undefined,
        is_income: formData.is_income,
        is_business: formData.is_business,
      })

      toast.success('Transaction added')
      setOpen(false)
      resetForm()
      onSuccess?.()
    } catch (error) {
      toast.error('Failed to add transaction')
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Transaction
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Transaction</DialogTitle>
          <DialogDescription>
            Manually add a transaction that wasn't imported from a bank statement.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Account */}
          <div className="space-y-2">
            <Label htmlFor="account">Account</Label>
            <Select
              value={formData.account_id}
              onValueChange={(value) => setFormData({ ...formData, account_id: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select account" />
              </SelectTrigger>
              <SelectContent>
                {accounts?.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.name}
                    {account.last4 && ` (****${account.last4})`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {accounts?.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No accounts found. Create an account first.
              </p>
            )}
          </div>

          {/* Date */}
          <div className="space-y-2">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="date"
              value={formData.posted_at}
              onChange={(e) => setFormData({ ...formData, posted_at: e.target.value })}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              placeholder="e.g., Grocery shopping at Walmart"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount</Label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="amount"
                type="number"
                step="0.01"
                placeholder="0.00"
                className="pl-9"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              />
            </div>
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label htmlFor="category">Category (optional)</Label>
            <Select
              value={formData.category_id}
              onValueChange={(value) => setFormData({ ...formData, category_id: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">None</SelectItem>
                {categories?.map((cat: { id: string; name: string }) => (
                  <SelectItem key={cat.id} value={cat.id}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Flags */}
          <div className="flex items-center gap-6">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_income"
                checked={formData.is_income}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, is_income: checked === true })
                }
              />
              <Label htmlFor="is_income" className="text-sm font-normal cursor-pointer">
                This is income
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_business"
                checked={formData.is_business}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, is_business: checked === true })
                }
              />
              <Label htmlFor="is_business" className="text-sm font-normal cursor-pointer">
                Business expense
              </Label>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createTransaction.isPending}
          >
            {createTransaction.isPending && (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            )}
            Add Transaction
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
