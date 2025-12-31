'use client'

import { useState, useEffect } from 'react'
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
import { Plus, Building, Car, GraduationCap, CreditCard, FileText, Package, Home, AlertCircle } from 'lucide-react'
import { useCreateLiability, useUpdateLiability, useLiabilities, useAssets, useCreateAsset, Liability, LiabilityCreate, Asset, AssetCreate } from '@/hooks/useNetWorth'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/components/ui/alert'

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
  editLiability?: Liability | null
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function AddLiabilityDialog({ trigger, onSuccess, editLiability, open: controlledOpen, onOpenChange }: AddLiabilityDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = onOpenChange || setInternalOpen

  const isEditMode = !!editLiability
  const [liabilityType, setLiabilityType] = useState<LiabilityCreate['liability_type']>('other')
  const createLiability = useCreateLiability()
  const updateLiability = useUpdateLiability()
  const createAsset = useCreateAsset()
  const { data: assets } = useAssets()

  const [formData, setFormData] = useState<Partial<LiabilityCreate>>({
    name: '',
    current_balance: 0,
  })

  // For creating asset alongside liability (mortgage/auto loan)
  const [createAssetToo, setCreateAssetToo] = useState(true)
  const [assetValue, setAssetValue] = useState<number | undefined>(undefined)
  const [assetName, setAssetName] = useState('')

  // Populate form when editing
  useEffect(() => {
    if (editLiability) {
      setLiabilityType(editLiability.liability_type)
      setFormData({
        name: editLiability.name,
        original_amount: editLiability.original_amount,
        current_balance: editLiability.current_balance,
        interest_rate: editLiability.interest_rate,
        monthly_payment: editLiability.monthly_payment,
        linked_asset_id: editLiability.linked_asset_id,
        start_date: editLiability.start_date,
        expected_payoff_date: editLiability.expected_payoff_date,
        lender: editLiability.lender,
        account_number: editLiability.account_number,
        notes: editLiability.notes,
      })
    }
  }, [editLiability])

  // Filter linkable assets based on liability type
  const linkableAssets = (assets || []).filter((asset: Asset) => {
    if (liabilityType === 'mortgage') return asset.asset_type === 'real_estate'
    if (liabilityType === 'auto_loan') return asset.asset_type === 'vehicle'
    return false
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Determine if we should create an asset alongside
    const shouldCreateAsset = !isEditMode &&
      (liabilityType === 'mortgage' || liabilityType === 'auto_loan') &&
      createAssetToo &&
      assetValue !== undefined &&
      assetValue > 0

    console.log('=== AddLiabilityDialog handleSubmit ===')
    console.log('isEditMode:', isEditMode)
    console.log('liabilityType:', liabilityType)
    console.log('createAssetToo:', createAssetToo)
    console.log('assetValue:', assetValue, typeof assetValue)
    console.log('assetName:', assetName)
    console.log('shouldCreateAsset:', shouldCreateAsset)
    console.log('formData:', formData)
    console.log('linkableAssets.length:', linkableAssets.length)

    try {
      let linkedAssetId: string | undefined = formData.linked_asset_id

      // For mortgage/auto loan: create asset first if user wants both
      if (shouldCreateAsset) {
        console.log('>>> Creating asset...')
        const assetType = liabilityType === 'mortgage' ? 'real_estate' : 'vehicle'
        const newAssetName = assetName || (liabilityType === 'mortgage' ? 'Property' : 'Vehicle')

        try {
          const newAsset = await createAsset.mutateAsync({
            name: newAssetName,
            asset_type: assetType,
            current_value: assetValue!,
          } as AssetCreate)

          console.log('>>> Asset created:', newAsset)

          if (newAsset?.id) {
            linkedAssetId = newAsset.id
            console.log('>>> Linking asset ID:', linkedAssetId)
          } else {
            console.warn('>>> Asset created but no ID returned!')
          }
        } catch (assetError) {
          console.error('>>> Failed to create asset:', assetError)
          // Continue to create liability anyway
        }
      } else {
        console.log('>>> Skipping asset creation - conditions not met')
      }

      if (isEditMode && editLiability) {
        console.log('>>> Updating liability...')
        await updateLiability.mutateAsync({
          id: editLiability.id,
          ...formData,
          liability_type: liabilityType,
          name: formData.name || '',
          current_balance: formData.current_balance || 0,
        } as Partial<Liability> & { id: string })
      } else {
        console.log('>>> Creating liability with linkedAssetId:', linkedAssetId)
        await createLiability.mutateAsync({
          ...formData,
          liability_type: liabilityType,
          name: formData.name || '',
          current_balance: formData.current_balance || 0,
          linked_asset_id: linkedAssetId,
        } as LiabilityCreate)
      }

      console.log('>>> Success! Closing dialog...')
      setOpen(false)
      if (!isEditMode) {
        setFormData({ name: '', current_balance: 0 })
        setLiabilityType('other')
        setAssetValue(undefined)
        setAssetName('')
        setCreateAssetToo(true)
      }
      onSuccess?.()
    } catch (error) {
      console.error('Failed to save liability:', error)
    }
  }

  const isLoading = createLiability.isPending || updateLiability.isPending || createAsset.isPending

  const updateField = (field: keyof LiabilityCreate, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {!isEditMode && (
        <DialogTrigger asChild>
          {trigger || (
            <Button variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Add Liability
            </Button>
          )}
        </DialogTrigger>
      )}
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditMode ? 'Edit Liability' : 'Add New Liability'}</DialogTitle>
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

          {/* Asset Creation/Linking for mortgage/auto loan */}
          {!isEditMode && (liabilityType === 'mortgage' || liabilityType === 'auto_loan') && (
            <div className="p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg space-y-3">
              <div className="flex items-start gap-2">
                <Home className="h-5 w-5 text-blue-600 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-medium text-sm text-blue-900 dark:text-blue-100">
                    {liabilityType === 'mortgage' ? 'Property Value' : 'Vehicle Value'}
                  </h4>
                  <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                    A {liabilityType === 'mortgage' ? 'mortgage' : 'auto loan'} is both a liability (what you owe) and an asset (what you own).
                    Enter the {liabilityType === 'mortgage' ? 'property' : 'vehicle'} value to track both.
                  </p>
                </div>
              </div>

              {linkableAssets.length > 0 ? (
                // If assets exist, let user choose to link or create new
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={createAssetToo ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCreateAssetToo(true)}
                    >
                      Create New
                    </Button>
                    <Button
                      type="button"
                      variant={!createAssetToo ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCreateAssetToo(false)}
                    >
                      Link Existing
                    </Button>
                  </div>

                  {createAssetToo ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label htmlFor="asset_name_create">{liabilityType === 'mortgage' ? 'Property Name' : 'Vehicle Name'}</Label>
                        <Input
                          id="asset_name_create"
                          value={assetName}
                          onChange={e => setAssetName(e.target.value)}
                          placeholder={liabilityType === 'mortgage' ? 'e.g., Primary Residence' : 'e.g., 2022 Toyota Camry'}
                        />
                      </div>
                      <div>
                        <Label htmlFor="asset_value_create">
                          Current Value ($) <span className="text-destructive">*</span>
                        </Label>
                        <Input
                          id="asset_value_create"
                          type="number"
                          step="0.01"
                          min="0"
                          value={assetValue ?? ''}
                          onChange={e => {
                            const val = e.target.value.replace(/,/g, '')
                            const num = parseFloat(val)
                            setAssetValue(isNaN(num) ? undefined : num)
                          }}
                          placeholder="e.g., 350000"
                        />
                      </div>
                    </div>
                  ) : (
                    <div>
                      <Label htmlFor="linked_asset_id">Select {liabilityType === 'mortgage' ? 'Property' : 'Vehicle'}</Label>
                      <Select
                        value={formData.linked_asset_id || 'none'}
                        onValueChange={v => updateField('linked_asset_id', v === 'none' ? undefined : v)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select asset to link" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">None</SelectItem>
                          {linkableAssets.map((asset: Asset) => (
                            <SelectItem key={asset.id} value={asset.id}>
                              {asset.name} (${asset.current_value.toLocaleString()})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
              ) : (
                // No existing assets - just show create form
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="asset_name_new">{liabilityType === 'mortgage' ? 'Property Name' : 'Vehicle Name'}</Label>
                    <Input
                      id="asset_name_new"
                      value={assetName}
                      onChange={e => setAssetName(e.target.value)}
                      placeholder={liabilityType === 'mortgage' ? 'e.g., Primary Residence' : 'e.g., 2022 Toyota Camry'}
                    />
                  </div>
                  <div>
                    <Label htmlFor="asset_value_new">
                      Current Value ($) <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="asset_value_new"
                      type="number"
                      step="0.01"
                      min="0"
                      value={assetValue ?? ''}
                      onChange={e => {
                        const val = e.target.value.replace(/,/g, '')
                        const num = parseFloat(val)
                        setAssetValue(isNaN(num) ? undefined : num)
                      }}
                      placeholder="e.g., 350000"
                    />
                  </div>
                </div>
              )}

              {assetValue && assetValue > 0 && formData.current_balance && formData.current_balance > 0 && (
                <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800">
                  <AlertCircle className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800 dark:text-green-200">
                    <strong>Equity:</strong> ${(assetValue - formData.current_balance).toLocaleString()}
                    ({((assetValue - formData.current_balance) / assetValue * 100).toFixed(1)}% of value)
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {/* Edit mode: Link to existing asset */}
          {isEditMode && (liabilityType === 'mortgage' || liabilityType === 'auto_loan') && linkableAssets.length > 0 && (
            <div className="p-3 bg-muted/50 rounded-lg space-y-3">
              <h4 className="font-medium text-sm">Link to Asset</h4>
              <div>
                <Label htmlFor="linked_asset_id">
                  {liabilityType === 'mortgage' ? 'Property' : 'Vehicle'}
                </Label>
                <Select
                  value={formData.linked_asset_id || 'none'}
                  onValueChange={v => updateField('linked_asset_id', v === 'none' ? undefined : v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select asset to link" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
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
            <Button type="submit" disabled={isLoading} variant={isEditMode ? "default" : "destructive"}>
              {isLoading ? (isEditMode ? 'Saving...' : 'Adding...') : (isEditMode ? 'Save Changes' : 'Add Liability')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
