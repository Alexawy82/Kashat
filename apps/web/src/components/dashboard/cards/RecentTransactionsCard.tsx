'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Receipt, ChevronRight, Search, Loader2 } from 'lucide-react'
import { format } from 'date-fns'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { toast } from '@/components/ui/Toaster'
import { useCategories, useAssignCategory } from '@/hooks/useCategories'
import { TransactionDetailModal } from '../modals/TransactionDetailModal'

interface Transaction {
  id: string
  date: string
  description: string
  merchant?: string
  amount: number
  category?: {
    id: string
    name: string
    color?: string
    icon?: string
  }
  account?: {
    id: string
    name: string
  }
  is_income?: boolean
  is_transfer?: boolean
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(Math.abs(value))
}

function useRecentTransactions(limit: number = 5) {
  return useQuery({
    queryKey: ['transactions', 'recent', limit],
    queryFn: async () => {
      const { data, error } = await client.get('/api/transactions', {
        params: {
          query: {
            limit,
            sort: '-date',
          },
        },
      })
      if (error) return []
      return ((data as { data?: Transaction[] })?.data || []) as Transaction[]
    },
    staleTime: 30000,
  })
}

export function RecentTransactionsCard() {
  const router = useRouter()
  const { data: transactions, isLoading } = useRecentTransactions(5)
  const { data: categories } = useCategories()
  const assignCategory = useAssignCategory()

  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null)
  const [editingCategory, setEditingCategory] = useState<string | null>(null)
  const [savingCategory, setSavingCategory] = useState(false)

  const handleCategoryChange = async (txId: string, categoryId: string) => {
    setSavingCategory(true)
    try {
      await assignCategory.mutateAsync({ txId, categoryId })
      toast.success('Category updated')
      setEditingCategory(null)
    } catch (error) {
      toast.error('Failed to update category')
    } finally {
      setSavingCategory(false)
    }
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Receipt className="h-5 w-5 text-green-500" />
              Recent Activity
            </CardTitle>

            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/transactions')}
                aria-label="Search transactions"
              >
                <Search className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/transactions')}
              >
                View All <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !transactions || transactions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Receipt className="h-10 w-10 mx-auto mb-2 opacity-50" />
              <p>No transactions yet</p>
              <Button
                variant="link"
                className="mt-2"
                onClick={() => router.push('/import')}
              >
                Import transactions
              </Button>
            </div>
          ) : (
            <div className="space-y-1">
              {transactions.map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between p-2 rounded cursor-pointer hover:bg-accent/50 -mx-2"
                  onClick={() => setSelectedTx(tx)}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* Category indicator - clickable to change */}
                    <Popover
                      open={editingCategory === tx.id}
                      onOpenChange={(open) => setEditingCategory(open ? tx.id : null)}
                    >
                      <PopoverTrigger asChild>
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center text-xs cursor-pointer hover:ring-2 ring-primary transition-all flex-shrink-0"
                          style={{
                            backgroundColor: tx.category?.color || '#e5e5e5',
                          }}
                          onClick={(e) => {
                            e.stopPropagation()
                            setEditingCategory(tx.id)
                          }}
                          title="Click to change category"
                        >
                          {tx.category?.icon || tx.category?.name?.charAt(0) || '?'}
                        </div>
                      </PopoverTrigger>
                      <PopoverContent className="w-48 p-2" align="start">
                        <div className="text-xs font-medium mb-2 text-muted-foreground">
                          Select Category
                        </div>
                        <div className="space-y-1 max-h-48 overflow-y-auto">
                          {categories?.map((cat: { id: string; name: string; color?: string }) => (
                            <div
                              key={cat.id}
                              className={cn(
                                'flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-accent text-sm',
                                tx.category?.id === cat.id && 'bg-accent'
                              )}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleCategoryChange(tx.id, cat.id)
                              }}
                            >
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: cat.color || '#888' }}
                              />
                              {cat.name}
                              {savingCategory && tx.category?.id === cat.id && (
                                <Loader2 className="h-3 w-3 animate-spin ml-auto" />
                              )}
                            </div>
                          ))}
                        </div>
                      </PopoverContent>
                    </Popover>

                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {tx.merchant || tx.description}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {format(new Date(tx.date), 'MMM d')}
                        {tx.category && ` · ${tx.category.name}`}
                      </div>
                    </div>
                  </div>

                  <span
                    className={cn(
                      'font-medium text-sm flex-shrink-0',
                      tx.amount < 0 ? 'text-red-600' : 'text-green-600'
                    )}
                  >
                    {tx.amount < 0 ? '-' : '+'}
                    {formatCurrency(tx.amount)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        transaction={selectedTx}
        open={!!selectedTx}
        onClose={() => setSelectedTx(null)}
        onEdit={() => {
          router.push(`/transactions?edit=${selectedTx?.id}`)
          setSelectedTx(null)
        }}
        onSplit={() => {
          toast.info('Split transaction feature coming soon')
        }}
      />
    </>
  )
}
