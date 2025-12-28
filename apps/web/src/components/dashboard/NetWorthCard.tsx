'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Wallet, TrendingUp, TrendingDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'
import { AnimatedCurrency } from '@/components/ui/AnimatedNumber'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'

interface NetWorthResponse {
  assets: number
  liabilities: number
  net_worth: number
  by_type: {
    checking: number
    savings: number
    investment: number
    asset: number
    credit_card: number
    loan: number
  }
  as_of: string
}

function useNetWorth() {
  return useQuery({
    queryKey: ['networth'],
    queryFn: async () => {
      const { data, error } = await client.get<NetWorthResponse>('/api/networth')
      if (error) throw error
      return data
    },
    staleTime: 60_000,
  })
}

export function NetWorthCard() {
  const { data, isLoading, isError } = useNetWorth()

  if (isLoading) return <CardSkeleton className="h-40" />
  if (isError) return <Card className="h-40 bg-destructive/10 border-destructive/20 dark:bg-destructive/20 flex items-center justify-center text-destructive text-sm">Error loading net worth</Card>

  const netWorth = data?.net_worth ?? 0
  const assets = data?.assets ?? 0
  const liabilities = data?.liabilities ?? 0
  const isPositive = netWorth >= 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Net Worth</CardTitle>
        <Wallet className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <AnimatedCurrency
            value={netWorth}
            className="text-3xl font-bold tracking-tighter"
            duration={800}
          />
          {isPositive ? (
            <TrendingUp className="h-4 w-4 text-green-500" aria-hidden="true" />
          ) : (
            <TrendingDown className="h-4 w-4 text-red-500" aria-hidden="true" />
          )}
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-muted-foreground">Assets</span>
            <p className="font-medium text-green-600 dark:text-green-400">
              ${assets.toLocaleString('en-US', { minimumFractionDigits: 0 })}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Liabilities</span>
            <p className="font-medium text-red-600 dark:text-red-400">
              ${liabilities.toLocaleString('en-US', { minimumFractionDigits: 0 })}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
