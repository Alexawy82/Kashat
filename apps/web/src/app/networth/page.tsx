'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  Edit,
  Building,
  CreditCard,
  GraduationCap,
  FileText,
  Loader2,
} from 'lucide-react'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'
import { AddAssetDialog } from '@/components/networth/AddAssetDialog'
import { AddLiabilityDialog } from '@/components/networth/AddLiabilityDialog'
import {
  useCompleteNetWorth,
  useAssets,
  useLiabilities,
  useDeleteAsset,
  useDeleteLiability,
  useRefreshMetalPrices,
  useMetalSpotPrices,
  Asset,
  Liability,
  ASSET_TYPE_LABELS,
  LIABILITY_TYPE_LABELS,
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

export default function NetWorthPage() {
  const { data: netWorth, isLoading: loadingNetWorth } = useCompleteNetWorth()
  const { data: assets, isLoading: loadingAssets } = useAssets()
  const { data: liabilities, isLoading: loadingLiabilities } = useLiabilities()
  const { data: metalPrices } = useMetalSpotPrices()
  const deleteAsset = useDeleteAsset()
  const deleteLiability = useDeleteLiability()
  const refreshMetals = useRefreshMetalPrices()

  const [activeTab, setActiveTab] = useState('overview')

  const handleDeleteAsset = async (id: string) => {
    if (confirm('Delete this asset?')) {
      await deleteAsset.mutateAsync(id)
    }
  }

  const handleDeleteLiability = async (id: string) => {
    if (confirm('Delete this liability?')) {
      await deleteLiability.mutateAsync(id)
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Net Worth</h1>
          <p className="text-muted-foreground">Track your complete financial picture</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshMetals.mutate()}
            disabled={refreshMetals.isPending}
          >
            {refreshMetals.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Update Metals
          </Button>
          <AddLiabilityDialog />
          <AddAssetDialog />
        </div>
      </div>

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
              <span>Manual: {formatCurrency(netWorth?.manual_assets ?? 0)}</span>
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
              {Object.entries(netWorth?.liability_breakdown ?? {}).slice(0, 3).map(([type, amount]) => (
                <Badge key={type} variant="outline" className="text-xs">
                  {LIABILITY_TYPE_LABELS[type as keyof typeof LIABILITY_TYPE_LABELS] || type}: {formatCurrency(amount as number)}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Asset Breakdown by Type */}
      {Object.keys(netWorth?.asset_breakdown ?? {}).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Asset Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {Object.entries(netWorth?.asset_breakdown ?? {}).map(([type, amount]) => {
                const Icon = ASSET_ICONS[type] || Package
                const percentage = totalAssets > 0 ? ((amount as number) / totalAssets) * 100 : 0
                return (
                  <div key={type} className="text-center p-3 bg-muted/50 rounded-lg">
                    <Icon className="h-6 w-6 mx-auto mb-2 text-primary" />
                    <div className="text-sm font-medium">
                      {ASSET_TYPE_LABELS[type as keyof typeof ASSET_TYPE_LABELS] || type}
                    </div>
                    <div className="text-lg font-bold">{formatCurrency(amount as number)}</div>
                    <div className="text-xs text-muted-foreground">{percentage.toFixed(1)}%</div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metal Spot Prices */}
      {metalPrices && (metalPrices.gold || metalPrices.silver || metalPrices.platinum || metalPrices.palladium) && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Coins className="h-5 w-5" />
              Live Spot Prices
            </CardTitle>
            <CardDescription>
              Updated: {new Date(metalPrices.as_of).toLocaleTimeString()}
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
          {/* Quick view of top assets and liabilities */}
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
                              <div className="font-medium">{asset.name}</div>
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
                              <div className="font-medium">{liability.name}</div>
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
          <Card>
            <CardContent className="pt-6">
              {loadingAssets ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                  ))}
                </div>
              ) : !assets?.length ? (
                <div className="text-center py-8">
                  <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-medium mb-2">No assets yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Add your real estate, vehicles, investments, and more
                  </p>
                  <AddAssetDialog />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Asset</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Value</TableHead>
                      <TableHead className="text-right">Purchase</TableHead>
                      <TableHead className="text-right">Gain/Loss</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {assets.map((asset: Asset) => {
                      const Icon = ASSET_ICONS[asset.asset_type] || Package
                      const gainLoss = asset.purchase_price
                        ? asset.current_value - asset.purchase_price
                        : null
                      return (
                        <TableRow key={asset.id}>
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <Icon className="h-5 w-5 text-muted-foreground" />
                              <div>
                                <div className="font-medium">{asset.name}</div>
                                {asset.metal_type && (
                                  <div className="text-xs text-muted-foreground">
                                    {asset.weight_oz} oz {asset.metal_type}
                                  </div>
                                )}
                                {asset.make && asset.model && (
                                  <div className="text-xs text-muted-foreground">
                                    {asset.year} {asset.make} {asset.model}
                                  </div>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">
                              {ASSET_TYPE_LABELS[asset.asset_type]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-medium text-green-600">
                            {formatCurrency(asset.current_value)}
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {asset.purchase_price ? formatCurrency(asset.purchase_price) : '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            {gainLoss !== null ? (
                              <span className={gainLoss >= 0 ? 'text-green-600' : 'text-red-600'}>
                                {gainLoss >= 0 ? '+' : ''}{formatCurrency(gainLoss)}
                              </span>
                            ) : '-'}
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={() => handleDeleteAsset(asset.id)}
                                  className="text-destructive"
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="liabilities">
          <Card>
            <CardContent className="pt-6">
              {loadingLiabilities ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-16 bg-muted animate-pulse rounded" />
                  ))}
                </div>
              ) : !liabilities?.length ? (
                <div className="text-center py-8">
                  <CreditCard className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-medium mb-2">No liabilities yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Track your mortgages, loans, and credit cards
                  </p>
                  <AddLiabilityDialog />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Liability</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Balance</TableHead>
                      <TableHead className="text-right">Rate</TableHead>
                      <TableHead className="text-right">Payment</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {liabilities.map((liability: Liability) => {
                      const Icon = LIABILITY_ICONS[liability.liability_type] || Package
                      return (
                        <TableRow key={liability.id}>
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <Icon className="h-5 w-5 text-muted-foreground" />
                              <div>
                                <div className="font-medium">{liability.name}</div>
                                {liability.lender && (
                                  <div className="text-xs text-muted-foreground">
                                    {liability.lender}
                                  </div>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="border-destructive/30 text-destructive">
                              {LIABILITY_TYPE_LABELS[liability.liability_type]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-medium text-red-600">
                            {formatCurrency(liability.current_balance)}
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {liability.interest_rate ? `${liability.interest_rate}%` : '-'}
                          </TableCell>
                          <TableCell className="text-right text-muted-foreground">
                            {liability.monthly_payment ? formatCurrency(liability.monthly_payment) : '-'}/mo
                          </TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onClick={() => handleDeleteLiability(liability.id)}
                                  className="text-destructive"
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
