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
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  TrendingUp,
  TrendingDown,
  ExternalLink,
  ChevronRight,
} from 'lucide-react'
import { useAnalyticsDashboard } from '@/hooks/useAnalytics'
import { cn } from '@/lib/utils'

interface ThisMonthModalProps {
  open: boolean
  onClose: () => void
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export function ThisMonthModal({ open, onClose }: ThisMonthModalProps) {
  const router = useRouter()
  const { data: analytics } = useAnalyticsDashboard()
  const [tab, setTab] = useState<'income' | 'spending'>('spending')

  const income = analytics?.summary?.income ?? 0
  const spending = analytics?.summary?.spending ?? 0
  const net = analytics?.summary?.net ?? 0
  const savingsRate = analytics?.summary?.savings_rate_pct ?? 0

  const topCategories = analytics?.top_categories?.slice(0, 8) || []
  const merchants = analytics?.merchants?.slice(0, 8) || []

  const maxCategorySpend = Math.max(...topCategories.map((c: { total_amount?: number }) => c.total_amount || 0), 1)

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>This Month Summary</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950/30">
              <div className="text-xs text-green-600 dark:text-green-400">Income</div>
              <div className="text-lg font-bold text-green-700 dark:text-green-300">
                {formatCurrency(income)}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30">
              <div className="text-xs text-red-600 dark:text-red-400">Spent</div>
              <div className="text-lg font-bold text-red-700 dark:text-red-300">
                {formatCurrency(spending)}
              </div>
            </div>
            <div className={cn(
              "p-3 rounded-lg",
              net >= 0 ? "bg-blue-50 dark:bg-blue-950/30" : "bg-orange-50 dark:bg-orange-950/30"
            )}>
              <div className={cn(
                "text-xs",
                net >= 0 ? "text-blue-600 dark:text-blue-400" : "text-orange-600 dark:text-orange-400"
              )}>Saved</div>
              <div className={cn(
                "text-lg font-bold",
                net >= 0 ? "text-blue-700 dark:text-blue-300" : "text-orange-700 dark:text-orange-300"
              )}>
                {net >= 0 ? '+' : ''}{formatCurrency(net)}
              </div>
            </div>
          </div>

          {/* Savings Rate */}
          <div className="p-3 rounded-lg bg-accent/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">Savings Rate</span>
              <span className={cn(
                "font-bold",
                savingsRate >= 20 ? "text-green-600" :
                savingsRate >= 10 ? "text-yellow-600" :
                "text-red-600"
              )}>
                {savingsRate.toFixed(1)}%
              </span>
            </div>
            <Progress value={Math.min(Math.max(savingsRate, 0), 100)} className="h-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {savingsRate >= 20 ? 'Great! Above 20% target' :
               savingsRate >= 10 ? 'Good progress, aim for 20%' :
               savingsRate >= 0 ? 'Try to increase savings' :
               'Spending exceeds income'}
            </p>
          </div>

          <Separator />

          {/* Tabs for Income/Spending breakdown */}
          <Tabs value={tab} onValueChange={(v) => setTab(v as 'income' | 'spending')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="spending" className="text-sm">
                <TrendingDown className="h-4 w-4 mr-1" /> Spending
              </TabsTrigger>
              <TabsTrigger value="income" className="text-sm">
                <TrendingUp className="h-4 w-4 mr-1" /> Income
              </TabsTrigger>
            </TabsList>

            <TabsContent value="spending" className="mt-3 space-y-2">
              <div className="text-sm font-medium text-muted-foreground mb-2">Top Categories</div>
              {topCategories.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">No spending data</p>
              ) : (
                topCategories.map((cat: { category_id: string; category_name: string; total_amount?: number }) => (
                  <div
                    key={cat.category_id}
                    className="cursor-pointer hover:bg-accent/50 p-2 rounded -mx-2"
                    onClick={() => {
                      onClose()
                      router.push(`/transactions?category=${cat.category_id}`)
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm">{cat.category_name}</span>
                      <span className="text-sm font-medium">{formatCurrency(cat.total_amount || 0)}</span>
                    </div>
                    <Progress
                      value={((cat.total_amount || 0) / maxCategorySpend) * 100}
                      className="h-1.5"
                    />
                  </div>
                ))
              )}

              <Button
                variant="ghost"
                className="w-full mt-2"
                onClick={() => {
                  onClose()
                  router.push('/transactions')
                }}
              >
                View All Spending <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </TabsContent>

            <TabsContent value="income" className="mt-3 space-y-2">
              <div className="text-sm font-medium text-muted-foreground mb-2">Top Income Sources</div>
              {merchants.filter((m: { spend?: number }) => (m.spend || 0) < 0).length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  Income sources will appear here
                </p>
              ) : (
                merchants
                  .filter((m: { spend?: number }) => (m.spend || 0) < 0)
                  .map((m: { merchant: string; spend?: number; count?: number }) => (
                    <div
                      key={m.merchant}
                      className="flex items-center justify-between p-2 rounded hover:bg-accent/50 cursor-pointer -mx-2"
                      onClick={() => {
                        onClose()
                        router.push(`/transactions?search=${encodeURIComponent(m.merchant)}`)
                      }}
                    >
                      <span className="text-sm truncate flex-1">{m.merchant}</span>
                      <span className="text-sm font-medium text-green-600">
                        {formatCurrency(Math.abs(m.spend || 0))}
                      </span>
                    </div>
                  ))
              )}
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={() => {
            onClose()
            router.push('/transactions')
          }}>
            View Transactions <ExternalLink className="h-4 w-4 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
