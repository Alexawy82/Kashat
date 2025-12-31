'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  TrendingUp,
  TrendingDown,
  Home,
  Car,
  Coins,
  Briefcase,
  Package,
  Plus,
  RefreshCw,
  MoreHorizontal,
  Trash2,
  Building,
  CreditCard,
  GraduationCap,
  FileText,
  Loader2,
  Lightbulb,
  Check,
  X,
  Clock,
  Link2,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Pencil,
} from 'lucide-react'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { PageHeader } from '@/components/ui/page-header'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'
import { AddAssetDialog } from '@/components/networth/AddAssetDialog'
import { AddLiabilityDialog } from '@/components/networth/AddLiabilityDialog'
import { toast } from '@/components/ui/Toaster'
import { useConfirm } from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils'
import {
  useCompleteNetWorth,
  useAssets,
  useLiabilities,
  useDeleteAsset,
  useDeleteLiability,
  useRefreshMetalPrices,
  useMetalSpotPrices,
  useNetWorthSuggestions,
  useAcceptSuggestion,
  useDismissSuggestion,
  useSnoozeSuggestion,
  useEnrichAsset,
  useRefreshAllAssets,
  Asset,
  Liability,
  NetWorthSuggestion,
  ASSET_TYPE_LABELS,
  LIABILITY_TYPE_LABELS,
  formatConfidence,
} from '@/hooks/useNetWorth'

const ASSET_ICONS: Record<string, React.ElementType> = {
  real_estate: Home,
  vehicle: Car,
  precious_metal: Coins,
  investment: TrendingUp,
  business: Briefcase,
  other: Package,
}

const LIABILITY_ICONS: Record<string, React.ElementType> = {
  mortgage: Building,
  auto_loan: Car,
  student_loan: GraduationCap,
  credit_card: CreditCard,
  personal_loan: FileText,
  other: Package,
}

const SUGGESTION_ICONS: Record<string, React.ElementType> = {
  property: Home,
  vehicle: Car,
  investment: TrendingUp,
  precious_metal: Coins,
  loan: CreditCard,
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// =============================================================================
// SUGGESTION DETAIL MODAL
// =============================================================================

function SuggestionDetailModal({
  suggestion,
  open,
  onClose,
  onAccept,
  onDismiss,
  onSnooze,
  isLoading,
}: {
  suggestion: NetWorthSuggestion | null
  open: boolean
  onClose: () => void
  onAccept: (overrides?: Record<string, any>) => void
  onDismiss: () => void
  onSnooze: () => void
  isLoading: boolean
}) {
  const [overrides, setOverrides] = useState<Record<string, any>>({})

  if (!suggestion) return null

  const Icon = SUGGESTION_ICONS[suggestion.type] || Lightbulb

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-primary" />
            {suggestion.type === 'property' && suggestion.subtype === 'mortgage'
              ? 'Mortgage Detected'
              : suggestion.type === 'vehicle'
                ? 'Auto Loan Detected'
                : suggestion.type === 'investment'
                  ? 'Investment Account Detected'
                  : suggestion.type === 'precious_metal'
                    ? 'Metal Purchase Detected'
                    : 'Asset Detected'}
          </DialogTitle>
          <DialogDescription>
            Review and confirm this detected asset/liability
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Source Info */}
          <div className="p-4 bg-muted rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Detected from recurring payment</div>
            <div className="font-medium text-lg">
              {suggestion.source_data?.lender || suggestion.recurring_name || 'Unknown'}
            </div>
            {suggestion.source_data?.monthly_payment && (
              <div className="text-sm text-muted-foreground">
                {formatCurrency(suggestion.source_data.monthly_payment)}/month
              </div>
            )}
          </div>

          {/* Confidence */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Detection Confidence</span>
            <Badge
              variant="outline"
              className={cn(
                suggestion.confidence >= 0.75 && 'border-green-500 text-green-600',
                suggestion.confidence >= 0.5 && suggestion.confidence < 0.75 && 'border-yellow-500 text-yellow-600',
                suggestion.confidence < 0.5 && 'border-red-500 text-red-600'
              )}
            >
              {formatConfidence(suggestion.confidence)} ({Math.round(suggestion.confidence * 100)}%)
            </Badge>
          </div>

          {/* Suggested Values */}
          <div>
            <div className="text-sm font-medium mb-3">Estimated Details</div>
            <div className="grid grid-cols-2 gap-3">
              {suggestion.suggested_values?.original_amount && (
                <div>
                  <Label className="text-xs text-muted-foreground">Original Loan</Label>
                  <Input
                    type="number"
                    defaultValue={suggestion.suggested_values.original_amount}
                    onChange={(e) => setOverrides({ ...overrides, original_amount: parseFloat(e.target.value) })}
                  />
                </div>
              )}
              {suggestion.suggested_values?.current_balance && (
                <div>
                  <Label className="text-xs text-muted-foreground">Current Balance</Label>
                  <Input
                    type="number"
                    defaultValue={suggestion.suggested_values.current_balance}
                    onChange={(e) => setOverrides({ ...overrides, current_balance: parseFloat(e.target.value) })}
                  />
                </div>
              )}
              {suggestion.suggested_values?.interest_rate && (
                <div>
                  <Label className="text-xs text-muted-foreground">Interest Rate (%)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    defaultValue={(suggestion.suggested_values.interest_rate * 100).toFixed(2)}
                    onChange={(e) => setOverrides({ ...overrides, interest_rate: parseFloat(e.target.value) / 100 })}
                  />
                </div>
              )}
              {suggestion.suggested_values?.term_months && (
                <div>
                  <Label className="text-xs text-muted-foreground">Term (years)</Label>
                  <Input
                    type="number"
                    defaultValue={Math.round(suggestion.suggested_values.term_months / 12)}
                    onChange={(e) => setOverrides({ ...overrides, term_months: parseInt(e.target.value) * 12 })}
                  />
                </div>
              )}
              {suggestion.type === 'property' && (
                <div className="col-span-2">
                  <Label className="text-xs text-muted-foreground">Property Name</Label>
                  <Input
                    placeholder="e.g., Primary Residence"
                    onChange={(e) => setOverrides({ ...overrides, name: e.target.value })}
                  />
                </div>
              )}
              {suggestion.type === 'vehicle' && (
                <div className="col-span-2">
                  <Label className="text-xs text-muted-foreground">Vehicle Description</Label>
                  <Input
                    placeholder="e.g., 2022 Toyota Camry"
                    onChange={(e) => setOverrides({ ...overrides, name: e.target.value })}
                  />
                </div>
              )}
            </div>
          </div>

          {/* What will be created */}
          <div className="p-3 bg-green-50 dark:bg-green-950/30 rounded-lg text-sm">
            <div className="font-medium text-green-700 dark:text-green-300 mb-1">
              What will be added:
            </div>
            <ul className="text-green-600 dark:text-green-400 space-y-1">
              {(suggestion.type === 'property' || suggestion.type === 'vehicle') && (
                <>
                  <li>• 1 Asset ({suggestion.type === 'property' ? 'Real Estate' : 'Vehicle'})</li>
                  <li>• 1 Liability ({suggestion.type === 'property' ? 'Mortgage' : 'Auto Loan'})</li>
                  <li>• Linked to recurring payment for auto-tracking</li>
                </>
              )}
              {suggestion.type === 'investment' && (
                <li>• 1 Investment Asset (balance needs manual update)</li>
              )}
              {suggestion.type === 'precious_metal' && (
                <li>• 1 Precious Metal Asset (specify weight to get spot value)</li>
              )}
            </ul>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button
              className="flex-1"
              onClick={() => onAccept(overrides)}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Check className="h-4 w-4 mr-2" />
              )}
              Add to Net Worth
            </Button>
            <Button
              variant="outline"
              onClick={onSnooze}
              disabled={isLoading}
              title="Remind me later"
            >
              <Clock className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              onClick={onDismiss}
              disabled={isLoading}
              title="Not relevant"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// =============================================================================
// SUGGESTIONS SECTION
// =============================================================================

function SuggestionsSection() {
  const { data, isLoading } = useNetWorthSuggestions()
  const acceptSuggestion = useAcceptSuggestion()
  const dismissSuggestion = useDismissSuggestion()
  const snoozeSuggestion = useSnoozeSuggestion()

  const [selectedSuggestion, setSelectedSuggestion] = useState<NetWorthSuggestion | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  const suggestions = data?.suggestions || []

  const handleAccept = async (overrides?: Record<string, any>) => {
    if (!selectedSuggestion) return
    setActionLoading(true)
    try {
      await acceptSuggestion.mutateAsync({ suggestionId: selectedSuggestion.id, overrides })
      toast.success('Asset and liability added to your net worth!')
      setSelectedSuggestion(null)
    } catch {
      toast.error('Failed to add. Please try again.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDismiss = async () => {
    if (!selectedSuggestion) return
    setActionLoading(true)
    try {
      await dismissSuggestion.mutateAsync(selectedSuggestion.id)
      toast.success('Suggestion dismissed')
      setSelectedSuggestion(null)
    } catch {
      toast.error('Failed to dismiss')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSnooze = async () => {
    if (!selectedSuggestion) return
    setActionLoading(true)
    try {
      await snoozeSuggestion.mutateAsync({ suggestionId: selectedSuggestion.id, days: 7 })
      toast.success('Snoozed for 7 days')
      setSelectedSuggestion(null)
    } catch {
      toast.error('Failed to snooze')
    } finally {
      setActionLoading(false)
    }
  }

  if (isLoading) {
    return (
      <Card className="border-orange-200 dark:border-orange-900/50">
        <CardContent className="py-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (suggestions.length === 0) {
    return null
  }

  return (
    <>
      <Card className="border-orange-200 dark:border-orange-900/50 bg-gradient-to-r from-orange-50/50 to-yellow-50/50 dark:from-orange-950/20 dark:to-yellow-950/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-orange-500" />
              <CardTitle className="text-lg">Smart Suggestions</CardTitle>
              <Badge className="bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300">
                {suggestions.length} detected
              </Badge>
            </div>
            <Sparkles className="h-5 w-5 text-orange-400" />
          </div>
          <CardDescription>
            We found potential assets and liabilities from your recurring payments
          </CardDescription>
        </CardHeader>

        <CardContent>
          <div className="space-y-2">
            {suggestions.map((suggestion) => {
              const Icon = SUGGESTION_ICONS[suggestion.type] || Lightbulb
              return (
                <div
                  key={suggestion.id}
                  className="flex items-center justify-between p-4 bg-background rounded-lg cursor-pointer hover:bg-accent/50 transition-colors border"
                  onClick={() => setSelectedSuggestion(suggestion)}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-full bg-orange-100 dark:bg-orange-900/50">
                      <Icon className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <div className="font-medium">
                        {suggestion.type === 'property' && suggestion.subtype === 'mortgage'
                          ? 'Mortgage Payment Detected'
                          : suggestion.type === 'vehicle'
                            ? 'Auto Loan Detected'
                            : suggestion.type === 'investment'
                              ? 'Investment Contributions Detected'
                              : 'Asset Detected'}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {suggestion.source_data?.lender || suggestion.recurring_name || 'From recurring payments'}
                        {suggestion.source_data?.monthly_payment && (
                          <span> • {formatCurrency(suggestion.source_data.monthly_payment)}/mo</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="hidden sm:flex">
                      {formatConfidence(suggestion.confidence)}
                    </Badge>
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <SuggestionDetailModal
        suggestion={selectedSuggestion}
        open={!!selectedSuggestion}
        onClose={() => setSelectedSuggestion(null)}
        onAccept={handleAccept}
        onDismiss={handleDismiss}
        onSnooze={handleSnooze}
        isLoading={actionLoading}
      />
    </>
  )
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function NetWorthPage() {
  const { data: netWorth, isLoading: loadingNetWorth } = useCompleteNetWorth()
  const { data: assets, isLoading: loadingAssets } = useAssets()
  const { data: liabilities, isLoading: loadingLiabilities } = useLiabilities()
  const { data: metalPrices } = useMetalSpotPrices()
  const deleteAsset = useDeleteAsset()
  const deleteLiability = useDeleteLiability()
  const refreshMetals = useRefreshMetalPrices()
  const enrichAsset = useEnrichAsset()
  const refreshAllAssets = useRefreshAllAssets()
  const { confirm, ConfirmDialog } = useConfirm()

  const [activeTab, setActiveTab] = useState('overview')
  const [enrichingId, setEnrichingId] = useState<string | null>(null)
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null)
  const [editingLiability, setEditingLiability] = useState<Liability | null>(null)

  const handleDeleteAsset = async (id: string) => {
    const confirmed = await confirm({
      title: 'Delete Asset',
      description: 'Are you sure you want to delete this asset? This cannot be undone.',
      confirmLabel: 'Delete',
      variant: 'destructive',
    })
    if (confirmed) {
      await deleteAsset.mutateAsync(id)
      toast.success('Asset deleted')
    }
  }

  const handleDeleteLiability = async (id: string) => {
    const confirmed = await confirm({
      title: 'Delete Liability',
      description: 'Are you sure you want to delete this liability? This cannot be undone.',
      confirmLabel: 'Delete',
      variant: 'destructive',
    })
    if (confirmed) {
      await deleteLiability.mutateAsync(id)
      toast.success('Liability deleted')
    }
  }

  const handleEnrichAsset = async (id: string) => {
    setEnrichingId(id)
    try {
      await enrichAsset.mutateAsync(id)
      toast.success('Asset updated with latest market data')
    } catch {
      toast.error('Failed to fetch market data')
    } finally {
      setEnrichingId(null)
    }
  }

  const handleRefreshAll = async () => {
    try {
      const result = await refreshAllAssets.mutateAsync()
      toast.success(`Updated ${result.refreshed} assets`)
    } catch {
      toast.error('Failed to refresh')
    }
  }

  if (loadingNetWorth) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardSkeleton className="h-32" />
          <CardSkeleton className="h-32" />
          <CardSkeleton className="h-32" />
        </div>
        <CardSkeleton className="h-64" />
      </div>
    )
  }

  const netWorthValue = netWorth?.net_worth ?? 0
  const totalAssets = netWorth?.total_assets ?? 0
  const totalLiabilities = netWorth?.total_liabilities ?? 0
  const assetRatio = totalAssets > 0 ? ((totalAssets - totalLiabilities) / totalAssets) * 100 : 0

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="Net Worth"
        description="Track your complete financial picture"
        helpItems={[
          "Add assets like real estate, vehicles, investments, and precious metals",
          "Add liabilities like mortgages, auto loans, and credit cards",
          "Smart suggestions detect assets from your recurring payments (mortgages, auto loans)",
          "Precious metals update with live spot prices automatically",
          "Linked items track balance changes based on your recurring payments"
        ]}
        action={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshAll}
              disabled={refreshAllAssets.isPending}
            >
              {refreshAllAssets.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Refresh All
            </Button>
            <AddLiabilityDialog />
            <AddAssetDialog />
          </div>
        }
      />

      {/* SMART SUGGESTIONS */}
      <SuggestionsSection />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Net Worth Card */}
        <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Net Worth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <AnimatedCurrency
                value={netWorthValue}
                className={`text-3xl font-bold ${netWorthValue >= 0 ? 'text-green-600' : 'text-red-600'}`}
              />
              {netWorthValue >= 0 ? (
                <TrendingUp className="h-5 w-5 text-green-600" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-600" />
              )}
            </div>
            <Progress value={Math.max(0, Math.min(100, assetRatio))} className="mt-3 h-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {assetRatio.toFixed(0)}% equity ratio
            </p>
          </CardContent>
        </Card>

        {/* Total Assets Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Assets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(totalAssets)}
            </div>
            <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
              <span>Bank: {formatCurrency(netWorth?.bank_accounts ?? 0)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Total Liabilities Card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Liabilities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {formatCurrency(totalLiabilities)}
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {Object.entries(netWorth?.breakdown?.liabilities ?? {}).slice(0, 3).map(([type, data]) => (
                <Badge key={type} variant="outline" className="text-xs">
                  {type}: {formatCurrency(data.total)}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metal Spot Prices */}
      {metalPrices && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Coins className="h-5 w-5 text-yellow-500" />
                <CardTitle className="text-lg">Live Spot Prices</CardTitle>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => refreshMetals.mutate()}
                disabled={refreshMetals.isPending}
              >
                {refreshMetals.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            </div>
            <CardDescription>
              {metalPrices.source === 'fallback' ? 'Estimated prices' : `Updated: ${new Date(metalPrices.as_of).toLocaleTimeString()}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {metalPrices.gold && (
                <div className="p-3 bg-yellow-500/10 rounded-lg text-center">
                  <div className="text-sm text-muted-foreground">Gold</div>
                  <div className="text-xl font-bold text-yellow-600">${metalPrices.gold.toFixed(2)}/oz</div>
                </div>
              )}
              {metalPrices.silver && (
                <div className="p-3 bg-gray-300/20 rounded-lg text-center">
                  <div className="text-sm text-muted-foreground">Silver</div>
                  <div className="text-xl font-bold text-gray-600">${metalPrices.silver.toFixed(2)}/oz</div>
                </div>
              )}
              {metalPrices.platinum && (
                <div className="p-3 bg-blue-100/30 rounded-lg text-center">
                  <div className="text-sm text-muted-foreground">Platinum</div>
                  <div className="text-xl font-bold text-blue-600">${metalPrices.platinum.toFixed(2)}/oz</div>
                </div>
              )}
              {metalPrices.palladium && (
                <div className="p-3 bg-purple-100/30 rounded-lg text-center">
                  <div className="text-sm text-muted-foreground">Palladium</div>
                  <div className="text-xl font-bold text-purple-600">${metalPrices.palladium.toFixed(2)}/oz</div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Assets & Liabilities Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="assets">Assets ({assets?.length ?? 0})</TabsTrigger>
          <TabsTrigger value="liabilities">Liabilities ({liabilities?.length ?? 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Top Assets */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Top Assets</CardTitle>
                <AddAssetDialog
                  trigger={
                    <Button size="sm" variant="ghost">
                      <Plus className="h-4 w-4" />
                    </Button>
                  }
                />
              </CardHeader>
              <CardContent>
                {loadingAssets ? (
                  <div className="space-y-2">
                    <div className="h-12 bg-muted animate-pulse rounded" />
                    <div className="h-12 bg-muted animate-pulse rounded" />
                  </div>
                ) : !assets?.length ? (
                  <p className="text-muted-foreground text-center py-4">
                    No assets added yet
                  </p>
                ) : (
                  <div className="space-y-2">
                    {assets.slice(0, 5).map((asset: Asset) => {
                      const Icon = ASSET_ICONS[asset.asset_type] || Package
                      return (
                        <div key={asset.id} className="flex items-center justify-between p-2 bg-muted/30 rounded-lg">
                          <div className="flex items-center gap-3">
                            <Icon className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <div className="font-medium flex items-center gap-2">
                                {asset.name}
                                {(asset as any).linked_recurring_id && (
                                  <Badge variant="outline" className="text-xs">
                                    <Link2 className="h-3 w-3 mr-1" />
                                    Linked
                                  </Badge>
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {ASSET_TYPE_LABELS[asset.asset_type]}
                              </div>
                            </div>
                          </div>
                          <div className="text-right font-medium text-green-600">
                            {formatCurrency(asset.current_value)}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top Liabilities */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-lg">Top Liabilities</CardTitle>
                <AddLiabilityDialog
                  trigger={
                    <Button size="sm" variant="ghost">
                      <Plus className="h-4 w-4" />
                    </Button>
                  }
                />
              </CardHeader>
              <CardContent>
                {loadingLiabilities ? (
                  <div className="space-y-2">
                    <div className="h-12 bg-muted animate-pulse rounded" />
                    <div className="h-12 bg-muted animate-pulse rounded" />
                  </div>
                ) : !liabilities?.length ? (
                  <p className="text-muted-foreground text-center py-4">
                    No liabilities added yet
                  </p>
                ) : (
                  <div className="space-y-2">
                    {liabilities.slice(0, 5).map((liability: Liability) => {
                      const Icon = LIABILITY_ICONS[liability.liability_type] || Package
                      return (
                        <div key={liability.id} className="flex items-center justify-between p-2 bg-muted/30 rounded-lg">
                          <div className="flex items-center gap-3">
                            <Icon className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <div className="font-medium flex items-center gap-2">
                                {liability.name}
                                {(liability as any).linked_recurring_id && (
                                  <Badge variant="outline" className="text-xs">
                                    <Link2 className="h-3 w-3 mr-1" />
                                    Linked
                                  </Badge>
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {LIABILITY_TYPE_LABELS[liability.liability_type]}
                                {liability.interest_rate && ` @ ${liability.interest_rate}%`}
                              </div>
                            </div>
                          </div>
                          <div className="text-right font-medium text-red-600">
                            {formatCurrency(liability.current_balance)}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="assets">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Your Assets</h3>
            <AddAssetDialog />
          </div>
          {loadingAssets ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="pt-6">
                    <div className="h-32 bg-muted rounded" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : !assets?.length ? (
            <Card>
              <CardContent className="text-center py-12">
                <Package className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-semibold text-lg mb-2">No assets yet</h3>
                <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                  Start building your net worth by adding your real estate, vehicles, investments, and other valuable assets.
                </p>
                <AddAssetDialog />
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {assets.map((asset: Asset) => {
                const Icon = ASSET_ICONS[asset.asset_type] || Package
                const gainLoss = asset.purchase_price ? asset.current_value - asset.purchase_price : null
                const gainLossPercent = asset.purchase_price ? ((asset.current_value - asset.purchase_price) / asset.purchase_price) * 100 : null
                const isEnriching = enrichingId === asset.id
                const details = typeof asset.details === 'string' ? JSON.parse(asset.details || '{}') : (asset.details || {})
                const enrichmentData = typeof asset.enrichment_data === 'string' ? JSON.parse(asset.enrichment_data || '{}') : (asset.enrichment_data || {})

                return (
                  <Card key={asset.id} className="group hover:shadow-lg transition-shadow">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "p-2 rounded-lg",
                            asset.asset_type === 'real_estate' && "bg-blue-100 dark:bg-blue-900/30",
                            asset.asset_type === 'vehicle' && "bg-orange-100 dark:bg-orange-900/30",
                            asset.asset_type === 'precious_metal' && "bg-yellow-100 dark:bg-yellow-900/30",
                            asset.asset_type === 'investment' && "bg-green-100 dark:bg-green-900/30",
                            asset.asset_type === 'business' && "bg-purple-100 dark:bg-purple-900/30",
                            !['real_estate', 'vehicle', 'precious_metal', 'investment', 'business'].includes(asset.asset_type) && "bg-muted"
                          )}>
                            <Icon className={cn(
                              "h-5 w-5",
                              asset.asset_type === 'real_estate' && "text-blue-600",
                              asset.asset_type === 'vehicle' && "text-orange-600",
                              asset.asset_type === 'precious_metal' && "text-yellow-600",
                              asset.asset_type === 'investment' && "text-green-600",
                              asset.asset_type === 'business' && "text-purple-600"
                            )} />
                          </div>
                          <div>
                            <CardTitle className="text-base">{asset.name}</CardTitle>
                            <CardDescription className="text-xs">
                              {ASSET_TYPE_LABELS[asset.asset_type]}
                            </CardDescription>
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setEditingAsset(asset)}>
                              <Pencil className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleEnrichAsset(asset.id)} disabled={isEnriching}>
                              {isEnriching ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                              Refresh Value
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDeleteAsset(asset.id)} className="text-destructive">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {/* Value */}
                      <div>
                        <div className="text-2xl font-bold text-green-600">
                          {formatCurrency(asset.current_value)}
                        </div>
                        {gainLoss !== null && (
                          <div className={cn("text-sm flex items-center gap-1", gainLoss >= 0 ? "text-green-600" : "text-red-600")}>
                            {gainLoss >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                            {gainLoss >= 0 ? '+' : ''}{formatCurrency(gainLoss)} ({gainLossPercent?.toFixed(1)}%)
                          </div>
                        )}
                      </div>

                      {/* Type-specific details */}
                      <div className="text-sm space-y-1 text-muted-foreground">
                        {/* Vehicle */}
                        {asset.asset_type === 'vehicle' && (details.year || details.make) && (
                          <div className="flex items-center gap-2">
                            <Car className="h-3 w-3" />
                            <span>{details.year} {details.make} {details.model}</span>
                          </div>
                        )}
                        {details.vin && (
                          <div className="text-xs font-mono truncate">VIN: {details.vin}</div>
                        )}

                        {/* Real Estate */}
                        {asset.asset_type === 'real_estate' && details.address && (
                          <div className="flex items-center gap-2">
                            <Home className="h-3 w-3" />
                            <span className="truncate">{details.address}</span>
                          </div>
                        )}

                        {/* Precious Metal */}
                        {asset.asset_type === 'precious_metal' && details.weight_oz && (
                          <div className="flex items-center gap-2">
                            <Coins className="h-3 w-3" />
                            <span>{details.weight_oz} oz {details.metal_type}</span>
                          </div>
                        )}

                        {/* Investment */}
                        {asset.asset_type === 'investment' && (details.ticker || details.institution) && (
                          <>
                            {details.ticker && (
                              <div className="flex items-center gap-2">
                                <TrendingUp className="h-3 w-3" />
                                <span className="font-mono">{details.ticker}</span>
                                {details.shares && <span>× {details.shares} shares</span>}
                              </div>
                            )}
                            {details.institution && (
                              <div>{details.institution} {details.account_type && `(${details.account_type.toUpperCase()})`}</div>
                            )}
                          </>
                        )}

                        {/* Purchase info */}
                        {asset.purchase_price && (
                          <div className="pt-1 border-t text-xs">
                            Purchased: {formatCurrency(asset.purchase_price)}
                            {asset.purchase_date && ` on ${new Date(asset.purchase_date).toLocaleDateString()}`}
                          </div>
                        )}
                      </div>

                      {/* Badges */}
                      <div className="flex flex-wrap gap-1.5 pt-2">
                        {(asset as any).linked_recurring_id && (
                          <Badge variant="secondary" className="text-xs">
                            <Link2 className="h-3 w-3 mr-1" />
                            Auto-tracked
                          </Badge>
                        )}
                        {(asset as any).last_enriched_at && (
                          <Badge variant="outline" className="text-xs border-green-300 text-green-600">
                            <Sparkles className="h-3 w-3 mr-1" />
                            Live Price
                          </Badge>
                        )}
                        {enrichmentData.source && (
                          <Badge variant="outline" className="text-xs">
                            via {enrichmentData.source}
                          </Badge>
                        )}
                      </div>

                      {/* Enrich button for enrichable assets */}
                      {['precious_metal', 'investment'].includes(asset.asset_type) && !(asset as any).last_enriched_at && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full mt-2"
                          onClick={() => handleEnrichAsset(asset.id)}
                          disabled={isEnriching}
                        >
                          {isEnriching ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                          Get Live Price
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="liabilities">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Your Liabilities</h3>
            <AddLiabilityDialog />
          </div>
          {loadingLiabilities ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="pt-6">
                    <div className="h-32 bg-muted rounded" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : !liabilities?.length ? (
            <Card>
              <CardContent className="text-center py-12">
                <CreditCard className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-semibold text-lg mb-2">No liabilities yet</h3>
                <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                  Track your mortgages, auto loans, student loans, and credit cards to see your complete financial picture.
                </p>
                <AddLiabilityDialog />
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {liabilities.map((liability: Liability) => {
                const Icon = LIABILITY_ICONS[liability.liability_type] || Package
                const paidOff = liability.original_amount ? liability.original_amount - liability.current_balance : 0
                const paidOffPercent = liability.original_amount ? (paidOff / liability.original_amount) * 100 : 0
                const monthlyInterest = liability.interest_rate && liability.current_balance
                  ? (liability.current_balance * (liability.interest_rate / 100)) / 12
                  : 0
                const monthsToPay = liability.monthly_payment && liability.monthly_payment > monthlyInterest
                  ? Math.ceil(liability.current_balance / (liability.monthly_payment - monthlyInterest))
                  : null

                return (
                  <Card key={liability.id} className="group hover:shadow-lg transition-shadow border-l-4 border-l-red-500">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "p-2 rounded-lg",
                            liability.liability_type === 'mortgage' && "bg-red-100 dark:bg-red-900/30",
                            liability.liability_type === 'auto_loan' && "bg-orange-100 dark:bg-orange-900/30",
                            liability.liability_type === 'student_loan' && "bg-blue-100 dark:bg-blue-900/30",
                            liability.liability_type === 'credit_card' && "bg-purple-100 dark:bg-purple-900/30",
                            !['mortgage', 'auto_loan', 'student_loan', 'credit_card'].includes(liability.liability_type) && "bg-muted"
                          )}>
                            <Icon className={cn(
                              "h-5 w-5",
                              liability.liability_type === 'mortgage' && "text-red-600",
                              liability.liability_type === 'auto_loan' && "text-orange-600",
                              liability.liability_type === 'student_loan' && "text-blue-600",
                              liability.liability_type === 'credit_card' && "text-purple-600"
                            )} />
                          </div>
                          <div>
                            <CardTitle className="text-base">{liability.name}</CardTitle>
                            <CardDescription className="text-xs">
                              {LIABILITY_TYPE_LABELS[liability.liability_type]}
                              {liability.lender && ` • ${liability.lender}`}
                            </CardDescription>
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setEditingLiability(liability)}>
                              <Pencil className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDeleteLiability(liability.id)} className="text-destructive">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {/* Balance */}
                      <div>
                        <div className="text-2xl font-bold text-red-600">
                          {formatCurrency(liability.current_balance)}
                        </div>
                        {liability.original_amount && (
                          <div className="text-sm text-muted-foreground">
                            of {formatCurrency(liability.original_amount)} original
                          </div>
                        )}
                      </div>

                      {/* Payoff Progress */}
                      {liability.original_amount && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Paid off</span>
                            <span className="font-medium text-green-600">{paidOffPercent.toFixed(0)}%</span>
                          </div>
                          <Progress value={paidOffPercent} className="h-2" />
                        </div>
                      )}

                      {/* Details */}
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        {liability.interest_rate && (
                          <div className="bg-muted/50 rounded-lg p-2">
                            <div className="text-xs text-muted-foreground">Interest Rate</div>
                            <div className="font-semibold">{liability.interest_rate}%</div>
                          </div>
                        )}
                        {liability.monthly_payment && (
                          <div className="bg-muted/50 rounded-lg p-2">
                            <div className="text-xs text-muted-foreground">Monthly Payment</div>
                            <div className="font-semibold">{formatCurrency(liability.monthly_payment)}</div>
                          </div>
                        )}
                      </div>

                      {/* Time to payoff */}
                      {monthsToPay && monthsToPay < 600 && (
                        <div className="text-sm text-muted-foreground border-t pt-2">
                          <Clock className="h-3 w-3 inline mr-1" />
                          ~{monthsToPay < 12 ? `${monthsToPay} months` : `${Math.round(monthsToPay / 12)} years`} to pay off
                        </div>
                      )}

                      {/* Badges */}
                      <div className="flex flex-wrap gap-1.5 pt-2">
                        {(liability as any).linked_recurring_id && (
                          <Badge variant="secondary" className="text-xs">
                            <Link2 className="h-3 w-3 mr-1" />
                            Auto-tracked
                          </Badge>
                        )}
                        {(liability as any).linked_asset_id && (
                          <Badge variant="outline" className="text-xs">
                            <Home className="h-3 w-3 mr-1" />
                            Linked Asset
                          </Badge>
                        )}
                        {liability.interest_rate && liability.interest_rate > 15 && (
                          <Badge variant="destructive" className="text-xs">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            High Interest
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Edit Asset Dialog */}
      <AddAssetDialog
        editAsset={editingAsset}
        open={!!editingAsset}
        onOpenChange={(open) => !open && setEditingAsset(null)}
        onSuccess={() => {
          setEditingAsset(null)
          toast.success('Asset updated')
        }}
      />

      {/* Edit Liability Dialog */}
      <AddLiabilityDialog
        editLiability={editingLiability}
        open={!!editingLiability}
        onOpenChange={(open) => !open && setEditingLiability(null)}
        onSuccess={() => {
          setEditingLiability(null)
          toast.success('Liability updated')
        }}
      />

      {/* Confirm Dialog */}
      <ConfirmDialog />
    </div>
  )
}
