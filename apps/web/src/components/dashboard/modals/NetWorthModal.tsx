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
import { Separator } from '@/components/ui/separator'
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Building2,
  Car,
  Coins,
  TrendingUp,
  Briefcase,
  Package,
  CreditCard,
  Home,
  GraduationCap,
  ExternalLink,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface AssetItem {
  id: string
  name: string
  value: number
}

interface AssetGroup {
  type: string
  label: string
  total: number
  items: AssetItem[]
}

interface NetWorthBreakdown {
  assets: AssetGroup[]
  liabilities: AssetGroup[]
  netWorth: number
}

interface NetWorthModalProps {
  open: boolean
  onClose: () => void
  breakdown?: NetWorthBreakdown
}

const assetIcons: Record<string, React.ReactNode> = {
  checking: <Building2 className="h-4 w-4" />,
  savings: <Coins className="h-4 w-4" />,
  investment: <TrendingUp className="h-4 w-4" />,
  real_estate: <Home className="h-4 w-4" />,
  vehicle: <Car className="h-4 w-4" />,
  business: <Briefcase className="h-4 w-4" />,
  other: <Package className="h-4 w-4" />,
  credit_card: <CreditCard className="h-4 w-4" />,
  mortgage: <Home className="h-4 w-4" />,
  auto_loan: <Car className="h-4 w-4" />,
  student_loan: <GraduationCap className="h-4 w-4" />,
  personal_loan: <Coins className="h-4 w-4" />,
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export function NetWorthModal({ open, onClose, breakdown }: NetWorthModalProps) {
  const router = useRouter()
  const [expandedType, setExpandedType] = useState<string | null>(null)

  const handleViewFull = () => {
    onClose()
    router.push('/networth')
  }

  const assets = breakdown?.assets || []
  const liabilities = breakdown?.liabilities || []
  const totalAssets = assets.reduce((sum, a) => sum + a.total, 0)
  const totalLiabilities = liabilities.reduce((sum, l) => sum + l.total, 0)

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Net Worth Breakdown</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Assets Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm text-muted-foreground">Assets</span>
              <span className="font-semibold text-green-600">{formatCurrency(totalAssets)}</span>
            </div>

            {assets.length === 0 ? (
              <p className="text-sm text-muted-foreground py-2">No assets tracked</p>
            ) : (
              assets.map((asset) => (
                <div key={asset.type} className="mb-1">
                  <div
                    className="flex items-center justify-between p-2 rounded hover:bg-accent cursor-pointer"
                    onClick={() => setExpandedType(expandedType === asset.type ? null : asset.type)}
                    role="button"
                    aria-expanded={expandedType === asset.type}
                  >
                    <div className="flex items-center gap-2">
                      {assetIcons[asset.type] || <Package className="h-4 w-4" />}
                      <span className="text-sm">{asset.label}</span>
                      {asset.items.length > 0 && (
                        <ChevronDown
                          className={cn(
                            'h-4 w-4 transition-transform text-muted-foreground',
                            expandedType === asset.type && 'rotate-180'
                          )}
                        />
                      )}
                    </div>
                    <span className="font-medium text-sm">{formatCurrency(asset.total)}</span>
                  </div>

                  {expandedType === asset.type && asset.items.length > 0 && (
                    <div className="ml-8 space-y-1 mt-1 mb-2">
                      {asset.items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-2 rounded hover:bg-accent/50 cursor-pointer text-sm"
                          onClick={() => router.push(`/networth?asset=${item.id}`)}
                        >
                          <span className="text-muted-foreground">{item.name}</span>
                          <span>{formatCurrency(item.value)}</span>
                        </div>
                      ))}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full mt-1 text-xs"
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/networth?add=${asset.type}`)
                        }}
                      >
                        <Plus className="h-3 w-3 mr-1" /> Add {asset.label}
                      </Button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <Separator />

          {/* Liabilities Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm text-muted-foreground">Liabilities</span>
              <span className="font-semibold text-red-600">{formatCurrency(totalLiabilities)}</span>
            </div>

            {liabilities.length === 0 ? (
              <p className="text-sm text-muted-foreground py-2">No liabilities tracked</p>
            ) : (
              liabilities.map((liability) => (
                <div key={liability.type} className="mb-1">
                  <div
                    className="flex items-center justify-between p-2 rounded hover:bg-accent cursor-pointer"
                    onClick={() =>
                      setExpandedType(expandedType === liability.type ? null : liability.type)
                    }
                  >
                    <div className="flex items-center gap-2">
                      {assetIcons[liability.type] || <CreditCard className="h-4 w-4" />}
                      <span className="text-sm">{liability.label}</span>
                      {liability.items.length > 0 && (
                        <ChevronDown
                          className={cn(
                            'h-4 w-4 transition-transform text-muted-foreground',
                            expandedType === liability.type && 'rotate-180'
                          )}
                        />
                      )}
                    </div>
                    <span className="font-medium text-sm text-red-600">
                      {formatCurrency(liability.total)}
                    </span>
                  </div>

                  {expandedType === liability.type && liability.items.length > 0 && (
                    <div className="ml-8 space-y-1 mt-1 mb-2">
                      {liability.items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-2 rounded hover:bg-accent/50 cursor-pointer text-sm"
                          onClick={() => router.push(`/networth?liability=${item.id}`)}
                        >
                          <span className="text-muted-foreground">{item.name}</span>
                          <span className="text-red-600">{formatCurrency(item.value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <Separator />

          {/* Net Worth Total */}
          <div className="flex justify-between items-center font-bold text-lg">
            <span>Net Worth</span>
            <span className={breakdown?.netWorth && breakdown.netWorth >= 0 ? 'text-green-600' : 'text-red-600'}>
              {formatCurrency(breakdown?.netWorth ?? 0)}
            </span>
          </div>
        </div>

        <DialogFooter className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={handleViewFull}>
            View Full Details <ExternalLink className="h-4 w-4 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
