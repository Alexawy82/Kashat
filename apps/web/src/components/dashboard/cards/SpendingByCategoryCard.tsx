'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PieChart, ChevronRight, Loader2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { CategoryTransactionsModal } from '../modals/CategoryTransactionsModal'

interface CategorySpending {
  id: string
  name: string
  amount: number
  percentage: number
  color?: string
  transaction_count?: number
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function useSpendingByCategory(period: string = 'month') {
  return useQuery({
    queryKey: ['spending-by-category', period],
    queryFn: async () => {
      const { data, error } = await client.get('/api/analytics/dashboard')
      if (error) return []

      const analytics = data as {
        top_categories?: Array<{
          category_id: string
          category_name: string
          total_amount?: number
          transaction_count?: number
        }>
        summary?: { spending?: number }
      }

      const totalSpending = analytics?.summary?.spending || 0
      const categories = analytics?.top_categories || []

      return categories.map((cat) => ({
        id: cat.category_id,
        name: cat.category_name,
        amount: cat.total_amount || 0,
        percentage: totalSpending > 0 ? ((cat.total_amount || 0) / totalSpending) * 100 : 0,
        transaction_count: cat.transaction_count,
        color: getCategoryColor(cat.category_name),
      }))
    },
    staleTime: 60000,
  })
}

function getCategoryColor(name: string): string {
  const colors: Record<string, string> = {
    'Grocery': '#22c55e',
    'Food & Dining': '#f97316',
    'Transportation': '#3b82f6',
    'Shopping': '#a855f7',
    'Entertainment': '#ec4899',
    'Utilities': '#eab308',
    'Healthcare': '#ef4444',
    'Housing': '#06b6d4',
    'Insurance': '#6366f1',
    'Education': '#14b8a6',
  }
  return colors[name] || '#6b7280'
}

export function SpendingByCategoryCard() {
  const router = useRouter()
  const [period, setPeriod] = useState<'month' | '30d' | '90d'>('month')
  const [selectedCategory, setSelectedCategory] = useState<CategorySpending | null>(null)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const { data: spending, isLoading } = useSpendingByCategory(period)

  const maxSpending = Math.max(...(spending?.map((c) => c.amount) || [0]), 1)

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <PieChart className="h-5 w-5 text-purple-500" />
              Spending
            </CardTitle>

            <Select value={period} onValueChange={(v) => setPeriod(v as typeof period)}>
              <SelectTrigger className="w-28 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="month">This Month</SelectItem>
                <SelectItem value="30d">Last 30 Days</SelectItem>
                <SelectItem value="90d">Last 90 Days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !spending || spending.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <PieChart className="h-10 w-10 mx-auto mb-2 opacity-50" />
              <p>No spending data yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {spending.slice(0, 5).map((category, idx) => (
                <div
                  key={category.id}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  onClick={() => setSelectedCategory(category)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className="text-sm font-medium hover:underline"
                      onClick={(e) => {
                        e.stopPropagation()
                        router.push(`/transactions?category=${category.id}`)
                      }}
                    >
                      {category.name}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {hoveredIdx === idx ? (
                        <span className="text-xs">
                          {category.percentage.toFixed(1)}% of total
                        </span>
                      ) : (
                        formatCurrency(category.amount)
                      )}
                    </span>
                  </div>
                  <div className="h-2 bg-accent rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-300',
                        hoveredIdx === idx ? 'opacity-80' : 'opacity-100'
                      )}
                      style={{
                        width: `${(category.amount / maxSpending) * 100}%`,
                        backgroundColor: category.color,
                      }}
                    />
                  </div>
                </div>
              ))}

              <Button
                variant="ghost"
                className="w-full mt-2"
                onClick={() => router.push('/transactions')}
              >
                View All Transactions <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Category Transactions Modal */}
      <CategoryTransactionsModal
        category={selectedCategory}
        open={!!selectedCategory}
        onClose={() => setSelectedCategory(null)}
        period={period}
      />
    </>
  )
}
