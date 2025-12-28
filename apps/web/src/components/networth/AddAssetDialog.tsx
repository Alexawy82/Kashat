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
import { Plus, Home, Car, Coins, TrendingUp, Briefcase, Package } from 'lucide-react'
import { useCreateAsset, AssetCreate, METAL_TYPES, PROPERTY_TYPES, INVESTMENT_ACCOUNT_TYPES } from '@/hooks/useNetWorth'
import { cn } from '@/lib/utils'

const ASSET_TYPES = [
  { value: 'real_estate', label: 'Real Estate', icon: Home },
  { value: 'vehicle', label: 'Vehicle', icon: Car },
  { value: 'precious_metal', label: 'Precious Metal', icon: Coins },
  { value: 'investment', label: 'Investment', icon: TrendingUp },
  { value: 'business', label: 'Business', icon: Briefcase },
  { value: 'other', label: 'Other', icon: Package },
] as const

interface AddAssetDialogProps {
  trigger?: React.ReactNode
  onSuccess?: () => void
}

export function AddAssetDialog({ trigger, onSuccess }: AddAssetDialogProps) {
  const [open, setOpen] = useState(false)
  const [assetType, setAssetType] = useState<AssetCreate['asset_type']>('other')
  const createAsset = useCreateAsset()

  const [formData, setFormData] = useState<Partial<AssetCreate>>({
    name: '',
    current_value: 0,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      await createAsset.mutateAsync({
        ...formData,
        asset_type: assetType,
        name: formData.name || '',
        current_value: formData.current_value || 0,
      } as AssetCreate)

      setOpen(false)
      setFormData({ name: '', current_value: 0 })
      setAssetType('other')
      onSuccess?.()
    } catch (error) {
      console.error('Failed to create asset:', error)
    }
  }

  const updateField = (field: keyof AssetCreate, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Asset
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Asset</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Asset Type Selection */}
          <div className="grid grid-cols-3 gap-2">
            {ASSET_TYPES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setAssetType(value)}
                className={cn(
                  'flex flex-col items-center gap-1 p-3 rounded-lg border transition-colors',
                  assetType === value
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border hover:border-primary/50'
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
                placeholder={assetType === 'real_estate' ? '123 Main St' : 'Asset name'}
                required
              />
            </div>

            <div>
              <Label htmlFor="current_value">Current Value ($)</Label>
              <Input
                id="current_value"
                type="number"
                step="0.01"
                value={formData.current_value || ''}
                onChange={e => updateField('current_value', parseFloat(e.target.value) || 0)}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="purchase_price">Purchase Price ($)</Label>
                <Input
                  id="purchase_price"
                  type="number"
                  step="0.01"
                  value={formData.purchase_price || ''}
                  onChange={e => updateField('purchase_price', parseFloat(e.target.value) || undefined)}
                />
              </div>
              <div>
                <Label htmlFor="purchase_date">Purchase Date</Label>
                <Input
                  id="purchase_date"
                  type="date"
                  value={formData.purchase_date || ''}
                  onChange={e => updateField('purchase_date', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Type-specific Fields */}
          {assetType === 'precious_metal' && (
            <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
              <h4 className="font-medium text-sm">Precious Metal Details</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="metal_type">Metal Type</Label>
                  <Select
                    value={formData.metal_type || ''}
                    onValueChange={v => updateField('metal_type', v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select metal" />
                    </SelectTrigger>
                    <SelectContent>
                      {METAL_TYPES.map(metal => (
                        <SelectItem key={metal} value={metal}>
                          {metal.charAt(0).toUpperCase() + metal.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="weight_oz">Weight (oz)</Label>
                  <Input
                    id="weight_oz"
                    type="number"
                    step="0.001"
                    value={formData.weight_oz || ''}
                    onChange={e => updateField('weight_oz', parseFloat(e.target.value) || undefined)}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="premium_paid">Premium Paid ($)</Label>
                <Input
                  id="premium_paid"
                  type="number"
                  step="0.01"
                  value={formData.premium_paid || ''}
                  onChange={e => updateField('premium_paid', parseFloat(e.target.value) || undefined)}
                  placeholder="Premium over spot price"
                />
              </div>
            </div>
          )}

          {assetType === 'real_estate' && (
            <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
              <h4 className="font-medium text-sm">Property Details</h4>
              <div>
                <Label htmlFor="address">Address</Label>
                <Input
                  id="address"
                  value={formData.address || ''}
                  onChange={e => updateField('address', e.target.value)}
                  placeholder="Full address"
                />
              </div>
              <div>
                <Label htmlFor="property_type">Property Type</Label>
                <Select
                  value={formData.property_type || ''}
                  onValueChange={v => updateField('property_type', v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {PROPERTY_TYPES.map(type => (
                      <SelectItem key={type} value={type}>
                        {type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {assetType === 'vehicle' && (
            <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
              <h4 className="font-medium text-sm">Vehicle Details</h4>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label htmlFor="year">Year</Label>
                  <Input
                    id="year"
                    type="number"
                    value={formData.year || ''}
                    onChange={e => updateField('year', parseInt(e.target.value) || undefined)}
                  />
                </div>
                <div>
                  <Label htmlFor="make">Make</Label>
                  <Input
                    id="make"
                    value={formData.make || ''}
                    onChange={e => updateField('make', e.target.value)}
                    placeholder="Toyota"
                  />
                </div>
                <div>
                  <Label htmlFor="model">Model</Label>
                  <Input
                    id="model"
                    value={formData.model || ''}
                    onChange={e => updateField('model', e.target.value)}
                    placeholder="Camry"
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="vin">VIN</Label>
                <Input
                  id="vin"
                  value={formData.vin || ''}
                  onChange={e => updateField('vin', e.target.value)}
                  placeholder="Vehicle Identification Number"
                />
              </div>
            </div>
          )}

          {assetType === 'investment' && (
            <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
              <h4 className="font-medium text-sm">Investment Details</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="institution">Institution</Label>
                  <Input
                    id="institution"
                    value={formData.institution || ''}
                    onChange={e => updateField('institution', e.target.value)}
                    placeholder="Fidelity, Vanguard, etc."
                  />
                </div>
                <div>
                  <Label htmlFor="account_type">Account Type</Label>
                  <Select
                    value={formData.account_type || ''}
                    onValueChange={v => updateField('account_type', v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {INVESTMENT_ACCOUNT_TYPES.map(type => (
                        <SelectItem key={type} value={type}>
                          {type.toUpperCase().replace('_', ' ')}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {assetType === 'business' && (
            <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
              <h4 className="font-medium text-sm">Business Details</h4>
              <div>
                <Label htmlFor="valuation_method">Valuation Method</Label>
                <Select
                  value={formData.valuation_method || ''}
                  onValueChange={v => updateField('valuation_method', v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="How is value calculated?" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="revenue_multiple">Revenue Multiple</SelectItem>
                    <SelectItem value="profit_multiple">Profit Multiple</SelectItem>
                    <SelectItem value="asset_based">Asset Based</SelectItem>
                    <SelectItem value="manual">Manual Estimate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="monthly_revenue">Monthly Revenue ($)</Label>
                  <Input
                    id="monthly_revenue"
                    type="number"
                    step="0.01"
                    value={formData.monthly_revenue || ''}
                    onChange={e => updateField('monthly_revenue', parseFloat(e.target.value) || undefined)}
                  />
                </div>
                <div>
                  <Label htmlFor="multiplier">Multiplier</Label>
                  <Input
                    id="multiplier"
                    type="number"
                    step="0.1"
                    value={formData.multiplier || ''}
                    onChange={e => updateField('multiplier', parseFloat(e.target.value) || undefined)}
                    placeholder="e.g., 3x"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Notes */}
          <div>
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              value={formData.notes || ''}
              onChange={e => updateField('notes', e.target.value)}
              placeholder="Optional notes about this asset"
              rows={2}
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createAsset.isPending}>
              {createAsset.isPending ? 'Adding...' : 'Add Asset'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
