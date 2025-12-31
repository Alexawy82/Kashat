'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { TrendingUp, TrendingDown, ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { NetWorthModal } from '../modals/NetWorthModal'

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

interface HeroNetWorthProps {
  netWorth: number
  change?: number
  changePercent?: number
  breakdown?: NetWorthBreakdown
  isLoading?: boolean
}

function formatCurrency(value: number): string {
  const absValue = Math.abs(value)
  if (absValue >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (absValue >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}

export function HeroNetWorth({
  netWorth,
  change = 0,
  changePercent = 0,
  breakdown,
  isLoading,
}: HeroNetWorthProps) {
  const [modalOpen, setModalOpen] = useState(false)

  if (isLoading) {
    return (
      <Card className="h-[120px] flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </Card>
    )
  }

  const isPositive = netWorth >= 0
  const changePositive = change >= 0

  return (
    <>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Card
              className="cursor-pointer hover:bg-accent/50 transition-all hover:shadow-md active:scale-[0.99]"
              onClick={() => setModalOpen(true)}
              role="button"
              aria-label="View net worth breakdown"
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground font-medium">Net Worth</span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>

                <div className="mt-2 flex items-baseline gap-2">
                  <span
                    className={cn(
                      'text-2xl md:text-3xl font-bold tracking-tight',
                      isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                    )}
                  >
                    <AnimatedCurrency value={netWorth} />
                  </span>
                  {isPositive ? (
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-red-600" />
                  )}
                </div>

                {change !== 0 && (
                  <div
                    className={cn(
                      'text-sm flex items-center gap-1 mt-2',
                      changePositive ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {changePositive ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    <span>
                      {changePositive ? '+' : ''}
                      {formatCurrency(change)}
                    </span>
                    <span className="text-muted-foreground">
                      ({changePercent >= 0 ? '+' : ''}
                      {changePercent.toFixed(1)}%) this month
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            <p>Click for detailed breakdown</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <NetWorthModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        breakdown={breakdown}
      />
    </>
  )
}
