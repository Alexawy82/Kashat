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
import { Badge } from '@/components/ui/badge'
import { Loader2, ChevronRight, ExternalLink } from 'lucide-react'
import { format } from 'date-fns'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { TransactionDetailModal } from './TransactionDetailModal'

interface Category {
  id: string
  name: string
  color?: string
  amount?: number
}

interface Transaction {
  id: string
  date: string
  description: string
  merchant?: string
  amount: number
  category?: { id: string; name: string; color?: string }
}

interface CategoryTransactionsModalProps {
  category: Category | null
  open: boolean
  onClose: () => void
  period?: 'month' | '30d' | '90d'
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(Math.abs(value))
}

export function CategoryTransactionsModal({
  category,
  open,
  onClose,
  period = 'month',
}: CategoryTransactionsModalProps) {
  const router = useRouter()
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null)

  const { data: transactions, isLoading } = useQuery({
    queryKey: ['category-transactions', category?.id, period],
    queryFn: async () => {
      if (!category?.id) return []
      const { data, error } = await client.get('/api/transactions', {
        params: {
          query: {
            category_id: category.id,
            limit: 20,
          },
        },
      })
      if (error) throw error
      return (data as { data?: Transaction[] })?.data || []
    },
    enabled: open && !!category?.id,
  })

  if (!category) return null

  return (
    <>
      <Dialog open={open && !selectedTx} onOpenChange={onClose}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: category.color || '#888' }}
              />
              {category.name}
              {category.amount && (
                <Badge variant="secondary">{formatCurrency(category.amount)}</Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-1 min-h-[200px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : transactions?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No transactions in this category</p>
              </div>
            ) : (
              transactions?.map((tx: Transaction) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between p-3 rounded cursor-pointer hover:bg-accent/50 -mx-2"
                  onClick={() => setSelectedTx(tx)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">
                      {tx.merchant || tx.description}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {format(new Date(tx.date), 'MMM d, yyyy')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "font-medium text-sm",
                      tx.amount < 0 ? "text-red-600" : "text-green-600"
                    )}>
                      {tx.amount < 0 ? '-' : '+'}{formatCurrency(tx.amount)}
                    </span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              ))
            )}
          </div>

          <DialogFooter className="flex gap-2 mt-4">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button
              onClick={() => {
                onClose()
                router.push(`/transactions?category=${category.id}`)
              }}
            >
              View All <ExternalLink className="h-4 w-4 ml-1" />
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Nested Transaction Detail Modal */}
      <TransactionDetailModal
        transaction={selectedTx}
        open={!!selectedTx}
        onClose={() => setSelectedTx(null)}
        onEdit={() => {
          router.push(`/transactions?edit=${selectedTx?.id}`)
          setSelectedTx(null)
          onClose()
        }}
      />
    </>
  )
}
