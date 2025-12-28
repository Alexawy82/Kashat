'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Plus, Building, Car, GraduationCap, CreditCard, FileText, Package } from 'lucide-react'
import { useCreateLiability, useLiabilities, useAssets, LiabilityCreate, Asset } from '@/hooks/useNetWorth'
import { cn } from '@/lib/utils'

const LIABILITY_TYPES = [
  { value: 'mortgage', label: 'Mortgage', icon: Building },
  { value: 'auto_loan', label: 'Auto Loan', icon: Car },
  { value: 'student_loan', label: 'Student Loan', icon: GraduationCap },
  { value: 'credit_card', label: 'Credit Card', icon: CreditCard },
  { value: 'personal_loan', label: 'Personal Loan', icon: FileText },
  { value: 'other', label: 'Other', icon: Package },
] as const

interface AddLiabilityDialogProps {
  trigger?: React.ReactNode
  onSuccess?: () => void
}

export function AddLiabilityDialog({ trigger, onSuccess }: AddLiabilityDialogProps) {
  const [open, setOpen] = useState(false)
  const [liabilityType, setLiabilityType] = useState<LiabilityCreate['liability_type']>('other')
  const createLiability = useCreateLiability()
  const { data: assets } = useAssets()

  const [formData, setFormData] = useState<Partial<LiabilityCreate>>({
    name: '',
    current_balance: 0,
  })

  // Filter linkable assets based on liability type
  const linkableAssets = (assets || []).filter((asset: Asset) => {
    if (liabilityType === 'mortgage') return asset.asset_type === 'real_estate'
    if (liabilityType === 'auto_loan') return asset.asset_type === 'vehicle'
    return false
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      await createLiability.mutateAsync({
        ...formData,
        liability_type: liabilityType,
        name: formData.name || '',
        current_balance: formData.current_balance || 0,
      } as LiabilityCreate)

      setOpen(false)
      setFormData({ name: '', current_balance: 0 })
      setLiabilityType('other')
      onSuccess?.()
    } catch (error) {
      console.error('Failed to create liability:', error)
    }
  }

  const updateField = (field: keyof LiabilityCreate, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <Plus className="h-4 w-4 mr-2" />
            Add Liability
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Liability</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Liability Type Selection */}
          <div className="grid grid-cols-3 gap-2">
            {LIABILITY_TYPES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setLiabilityType(value)
                  // Clear linked asset when changing type
                  updateField('linked_asset_id', undefined)
                }}
                className={cn(
                  'flex flex-col items-center gap-1 p-3 rounded-lg border transition-colors',
                  liabilityType === value
                    ? 'border-destructive bg-destructive/10 text-destructive'
                    : 'border-border hover:border-destructive/50'
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs">{label}</span>
              </button>
            ))}
          </div>

          {/* Common Fields */}
          <div className="space-y-3">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={formData.name || ''}
                onChange={e => updateField('name', e.target.value)}
                placeholder={liabilityType === 'mortgage' ? 'Home Mortgage' : 'Liability name'}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="original_amount">Original Amount ($)</Label>
                <Input
                  id="original_amount"
                  type="number"
                  step="0.01"
                  value={formData.original_amount || ''}
                  onChange={e => updateField('original_amount', parseFloat(e.target.value) || undefined)}
                />
              </div>
              <div>
                <Label htmlFor="current_balance">Current Balance ($)</Label>
                <Input
                  id="current_balance"
                  type="number"
                  step="0.01"
                  value={formData.current_balance || ''}
                  onChange={e => updateField('current_balance', parseFloat(e.target.value) || 0)}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="interest_rate">Interest Rate (%)</Label>
                <Input
                  id="interest_rate"
                  type="number"
                  step="0.01"
                  value={formData.interest_rate || ''}
                  onChange={e => updateField('interest_rate', parseFloat(e.target.value) || undefined)}
                  placeholder="e.g., 4.5"
                />
              </div>
              <div>
                <Label htmlFor="monthly_payment">Monthly Payment ($)</Label>
                <Input
                  id="monthly_payment"
                  type="number"
                  step="0.01"
                  value={formData.monthly_payment || ''}
                  onChange={e => updateField('monthly_payment', parseFloat(e.target.value) || undefined)}
                />
              </div>
            </div>
          </div>

          {/* Link to Asset (for mortgage/auto loan) */}
          {(liabilityType === 'mortgage' || liabilityType === 'auto_loan') && linkableAssets.length > 0 && (
            <div className="p-3 bg-muted/50 rounded-lg space-y-3">
              <h4 className="font-medium text-sm">Link to Asset</h4>
              <div>
                <Label htmlFor="linked_asset_id">
                  {liabilityType === 'mortgage' ? 'Property' : 'Vehicle'}
                </Label>
                <Select
                  value={formData.linked_asset_id || ''}
                  onValueChange={v => updateField('linked_asset_id', v || undefined)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select asset to link" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
                    {linkableAssets.map((asset: Asset) => (
                      <SelectItem key={asset.id} value={asset.id}>
                        {asset.name} (${asset.current_value.toLocaleString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* Lender & Dates */}
          <div className="space-y-3">
            <div>
              <Label htmlFor="lender">Lender</Label>
              <Input
                id="lender"
                value={formData.lender || ''}
                onChange={e => updateField('lender', e.target.value)}
                placeholder="Bank or lender name"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={formData.start_date || ''}
                  onChange={e => updateField('start_date', e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="expected_payoff_date">Expected Payoff</Label>
                <Input
                  id="expected_payoff_date"
                  type="date"
                  value={formData.expected_payoff_date || ''}
                  onChange={e => updateField('expected_payoff_date', e.target.value)}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="account_number">Account Number</Label>
              <Input
                id="account_number"
                value={formData.account_number || ''}
                onChange={e => updateField('account_number', e.target.value)}
                placeholder="Last 4 digits"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              value={formData.notes || ''}
              onChange={e => updateField('notes', e.target.value)}
              placeholder="Optional notes about this liability"
              rows={2}
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createLiability.isPending} variant="destructive">
              {createLiability.isPending ? 'Adding...' : 'Add Liability'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
