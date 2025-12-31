'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThisMonthModal } from '../modals/ThisMonthModal'

interface HeroThisMonthProps {
  income: number
  spending: number
  saved: number
  savingsRate: number
  isLoading?: boolean
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export function HeroThisMonth({
  income,
  spending,
  saved,
  savingsRate,
  isLoading,
}: HeroThisMonthProps) {
  const [modalOpen, setModalOpen] = useState(false)

  if (isLoading) {
    return (
      <Card className="h-[120px] flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </Card>
    )
  }

  return (
    <>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Card
              className="cursor-pointer hover:bg-accent/50 transition-all hover:shadow-md active:scale-[0.99]"
              onClick={() => setModalOpen(true)}
              role="button"
              aria-label="View this month's details"
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground font-medium">This Month</span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>

                <div className="mt-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Income</span>
                    <span className="text-green-600 font-medium">{formatCurrency(income)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Spent</span>
                    <span className="text-red-600 font-medium">-{formatCurrency(spending)}</span>
                  </div>
                  <Separator className="my-1" />
                  <div className="flex justify-between font-medium">
                    <span>Saved</span>
                    <span className={saved >= 0 ? 'text-green-600' : 'text-red-600'}>
                      {saved >= 0 ? '+' : ''}
                      {formatCurrency(saved)}
                    </span>
                  </div>
                </div>

                <div
                  className={cn(
                    'mt-2 text-xs',
                    savingsRate >= 20
                      ? 'text-green-600'
                      : savingsRate >= 10
                        ? 'text-yellow-600'
                        : 'text-red-600'
                  )}
                >
                  {savingsRate.toFixed(0)}% savings rate
                </div>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            <p>Click for income & spending breakdown</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <ThisMonthModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  )
}
