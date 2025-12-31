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
import { Plus, Home, Car, Coins, TrendingUp, Briefcase, Package, Search, Loader2, CheckCircle2, AlertCircle, CreditCard } from 'lucide-react'
import { AddressAutocomplete } from '@/components/ui/AddressAutocomplete'
import { useCreateAsset, useUpdateAsset, useCreateLiability, Asset, AssetCreate, LiabilityCreate, METAL_TYPES, PROPERTY_TYPES, INVESTMENT_ACCOUNT_TYPES, useDecodeVin, useStockPrice } from '@/hooks/useNetWorth'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Switch } from '@/components/ui/switch'

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
  editAsset?: Asset | null
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function AddAssetDialog({ trigger, onSuccess, editAsset, open: controlledOpen, onOpenChange }: AddAssetDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = onOpenChange || setInternalOpen

  const isEditMode = !!editAsset
  const [assetType, setAssetType] = useState<AssetCreate['asset_type']>('other')
  const [stockTicker, setStockTicker] = useState('')
  const [vinDecoded, setVinDecoded] = useState(false)
  const [stockLookedUp, setStockLookedUp] = useState(false)
  const createAsset = useCreateAsset()
  const updateAsset = useUpdateAsset()
  const createLiability = useCreateLiability()
  const decodeVin = useDecodeVin()
  const { data: stockData, isLoading: stockLoading, refetch: fetchStock } = useStockPrice(stockTicker)

  const [formData, setFormData] = useState<Partial<AssetCreate>>({
    name: '',
    current_value: 0,
  })

  // For creating liability alongside asset (mortgage/auto loan)
  const [hasLoan, setHasLoan] = useState(false)
  const [loanBalance, setLoanBalance] = useState<number | undefined>(undefined)
  const [loanName, setLoanName] = useState('')
  const [interestRate, setInterestRate] = useState<number | undefined>(undefined)
  const [monthlyPayment, setMonthlyPayment] = useState<number | undefined>(undefined)

  // Populate form when editing
  useEffect(() => {
    if (editAsset) {
      const details = typeof editAsset.details === 'string'
        ? JSON.parse(editAsset.details || '{}')
        : (editAsset.details || {})

      setAssetType(editAsset.asset_type)
      setFormData({
        name: editAsset.name,
        current_value: editAsset.current_value,
        purchase_price: editAsset.purchase_price,
        purchase_date: editAsset.purchase_date,
        notes: editAsset.notes,
        // Type-specific from details
        weight_oz: details.weight_oz || editAsset.weight_oz,
        metal_type: details.metal_type || editAsset.metal_type,
        premium_paid: details.premium_paid || editAsset.premium_paid,
        address: details.address || editAsset.address,
        property_type: details.property_type || editAsset.property_type,
        year: details.year || editAsset.year,
        make: details.make || editAsset.make,
        model: details.model || editAsset.model,
        vin: details.vin || editAsset.vin,
        institution: details.institution || editAsset.institution,
        account_type: details.account_type || editAsset.account_type,
        ticker: details.ticker,
        shares: details.shares,
        cost_basis: details.cost_basis,
        valuation_method: details.valuation_method || editAsset.valuation_method,
        monthly_revenue: details.monthly_revenue || editAsset.monthly_revenue,
        multiplier: details.multiplier || editAsset.multiplier,
      })
      if (details.ticker) setStockTicker(details.ticker)
    }
  }, [editAsset])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      if (isEditMode && editAsset) {
        await updateAsset.mutateAsync({
          id: editAsset.id,
          ...formData,
          asset_type: assetType,
          name: formData.name || '',
          current_value: formData.current_value || 0,
        } as Partial<Asset> & { id: string })
      } else {
        // Create the asset first
        const newAsset = await createAsset.mutateAsync({
          ...formData,
          asset_type: assetType,
          name: formData.name || '',
          current_value: formData.current_value || 0,
        } as AssetCreate)

        // For real_estate/vehicle: create liability if user has a loan
        if ((assetType === 'real_estate' || assetType === 'vehicle') && hasLoan && loanBalance && loanBalance > 0 && newAsset?.id) {
          const liabilityType = assetType === 'real_estate' ? 'mortgage' : 'auto_loan'
          const defaultLoanName = assetType === 'real_estate'
            ? `Mortgage - ${formData.name || 'Property'}`
            : `Auto Loan - ${formData.name || 'Vehicle'}`

          await createLiability.mutateAsync({
            name: loanName || defaultLoanName,
            liability_type: liabilityType,
            current_balance: loanBalance,
            original_amount: loanBalance,
            interest_rate: interestRate,
            monthly_payment: monthlyPayment,
            linked_asset_id: newAsset.id,
          } as LiabilityCreate)
        }
      }

      setOpen(false)
      if (!isEditMode) {
        setFormData({ name: '', current_value: 0 })
        setAssetType('other')
        setStockTicker('')
        setVinDecoded(false)
        setStockLookedUp(false)
        setHasLoan(false)
        setLoanBalance(undefined)
        setLoanName('')
        setInterestRate(undefined)
        setMonthlyPayment(undefined)
      }
      onSuccess?.()
    } catch (error) {
      console.error('Failed to save asset:', error)
    }
  }

  const isLoading = createAsset.isPending || updateAsset.isPending || createLiability.isPending

  const updateField = (field: keyof AssetCreate, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  // Handle VIN decode
  const handleDecodeVin = async () => {
    const vin = formData.vin
    if (!vin || vin.length < 11) return

    try {
      const result = await decodeVin.mutateAsync(vin)
      if (result) {
        setFormData(prev => ({
          ...prev,
          year: typeof result.year === 'string' ? parseInt(result.year) : (result.year || prev.year),
          make: result.make || prev.make,
          model: result.model || prev.model,
        }))
        setVinDecoded(true)
      }
    } catch (error) {
      console.error('VIN decode failed:', error)
    }
  }

  // Handle stock lookup - use effect to apply data when it loads
  const handleStockLookup = async () => {
    if (!stockTicker) return
    const result = await fetchStock()
    if (result.data) {
      setFormData(prev => ({
        ...prev,
        ticker: stockTicker.toUpperCase(),
        current_value: result.data.price || prev.current_value,
        name: prev.name || result.data.name || stockTicker.toUpperCase(),
      }))
      setStockLookedUp(true)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {!isEditMode && (
        <DialogTrigger asChild>
          {trigger || (
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Asset
            </Button>
          )}
        </DialogTrigger>
      )}
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditMode ? 'Edit Asset' : 'Add New Asset'}</DialogTitle>
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
                    value={formData.metal_type || undefined}
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
                <AddressAutocomplete
                  value={formData.address || ''}
                  onChange={(value, details) => {
                    updateField('address', value)
                    // Store full address details for enrichment
                    if (details) {
                      setFormData(prev => ({
                        ...prev,
                        address: value,
                        city: details.city,
                        state: details.state,
                        postcode: details.postcode,
                        lat: details.lat,
                        lon: details.lon,
                      }))
                    }
                  }}
                  placeholder="Start typing an address..."
                />
              </div>
              <div>
                <Label htmlFor="property_type">Property Type</Label>
                <Select
                  value={formData.property_type || undefined}
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
              {/* VIN with Decode Button */}
              <div>
                <Label htmlFor="vin">VIN (optional)</Label>
                <div className="flex gap-2">
                  <Input
                    id="vin"
                    value={formData.vin || ''}
                    onChange={e => {
                      updateField('vin', e.target.value.toUpperCase())
                      setVinDecoded(false)
                    }}
                    placeholder="Enter VIN to auto-fill details"
                    maxLength={17}
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleDecodeVin}
                    disabled={!formData.vin || formData.vin.length < 11 || decodeVin.isPending}
                    className="shrink-0"
                  >
                    {decodeVin.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : vinDecoded ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    <span className="ml-1">Decode</span>
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Enter VIN to auto-fill year, make, and model
                </p>
              </div>
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
            </div>
          )}

          {/* Loan Section for Real Estate and Vehicles */}
          {!isEditMode && (assetType === 'real_estate' || assetType === 'vehicle') && (
            <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-start gap-2">
                  <CreditCard className="h-5 w-5 text-amber-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-sm text-amber-900 dark:text-amber-100">
                      {assetType === 'real_estate' ? 'Mortgage' : 'Auto Loan'}
                    </h4>
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      Do you have a loan on this {assetType === 'real_estate' ? 'property' : 'vehicle'}?
                    </p>
                  </div>
                </div>
                <Switch
                  checked={hasLoan}
                  onCheckedChange={setHasLoan}
                />
              </div>

              {hasLoan && (
                <div className="space-y-3 pt-2 border-t border-amber-200 dark:border-amber-700">
                  <div>
                    <Label htmlFor="loan_name">Loan Name</Label>
                    <Input
                      id="loan_name"
                      value={loanName}
                      onChange={e => setLoanName(e.target.value)}
                      placeholder={assetType === 'real_estate' ? 'e.g., Chase Mortgage' : 'e.g., Toyota Financial'}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="loan_balance">Current Balance ($)</Label>
                      <Input
                        id="loan_balance"
                        type="number"
                        step="0.01"
                        value={loanBalance || ''}
                        onChange={e => setLoanBalance(parseFloat(e.target.value) || undefined)}
                        placeholder="Amount owed"
                      />
                    </div>
                    <div>
                      <Label htmlFor="interest_rate">Interest Rate (%)</Label>
                      <Input
                        id="interest_rate"
                        type="number"
                        step="0.01"
                        value={interestRate || ''}
                        onChange={e => setInterestRate(parseFloat(e.target.value) || undefined)}
                        placeholder="e.g., 6.5"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="monthly_payment">Monthly Payment ($)</Label>
                    <Input
                      id="monthly_payment"
                      type="number"
                      step="0.01"
                      value={monthlyPayment || ''}
                      onChange={e => setMonthlyPayment(parseFloat(e.target.value) || undefined)}
                      placeholder="Monthly payment amount"
                    />
                  </div>

                  {loanBalance && loanBalance > 0 && formData.current_value && formData.current_value > 0 && (
                    <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800">
                      <AlertCircle className="h-4 w-4 text-green-600" />
                      <AlertDescription className="text-green-800 dark:text-green-200">
                        <strong>Equity:</strong> ${(formData.current_value - loanBalance).toLocaleString()}
                        ({((formData.current_value - loanBalance) / formData.current_value * 100).toFixed(1)}% of value)
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}
            </div>
          )}

          {assetType === 'investment' && (
            <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
              <h4 className="font-medium text-sm">Investment Details</h4>
              {/* Stock Ticker Lookup */}
              <div>
                <Label htmlFor="ticker">Stock Ticker (optional)</Label>
                <div className="flex gap-2">
                  <Input
                    id="ticker"
                    value={stockTicker}
                    onChange={e => {
                      setStockTicker(e.target.value.toUpperCase())
                      setStockLookedUp(false)
                    }}
                    placeholder="AAPL, MSFT, TSLA..."
                    maxLength={10}
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleStockLookup}
                    disabled={!stockTicker || stockLoading}
                    className="shrink-0"
                  >
                    {stockLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : stockLookedUp ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    <span className="ml-1">Lookup</span>
                  </Button>
                </div>
                {stockData && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {stockData.name}: ${stockData.price?.toFixed(2)} ({stockData.change_percent?.toFixed(2)}%)
                  </p>
                )}
              </div>
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
                    value={formData.account_type || undefined}
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
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="shares">Number of Shares</Label>
                  <Input
                    id="shares"
                    type="number"
                    step="0.0001"
                    value={formData.shares || ''}
                    onChange={e => updateField('shares', parseFloat(e.target.value) || undefined)}
                    placeholder="100"
                  />
                </div>
                <div>
                  <Label htmlFor="cost_basis">Cost Basis ($)</Label>
                  <Input
                    id="cost_basis"
                    type="number"
                    step="0.01"
                    value={formData.cost_basis || ''}
                    onChange={e => updateField('cost_basis', parseFloat(e.target.value) || undefined)}
                    placeholder="Total cost"
                  />
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
                  value={formData.valuation_method || undefined}
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
            <Button type="submit" disabled={isLoading}>
              {isLoading ? (isEditMode ? 'Saving...' : 'Adding...') : (isEditMode ? 'Save Changes' : 'Add Asset')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
