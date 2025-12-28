"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowDownLeft,
  ArrowUpRight,
  Users,
  RefreshCw,
  Wallet,
} from "lucide-react"
import type { P2PStats } from "@/hooks/useP2P"

interface StatsCardsProps {
  stats: P2PStats | undefined
  isLoading: boolean
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))
}

export function StatsCards({ stats, isLoading }: StatsCardsProps) {
  // Calculate totals from stats
  const totalSent = stats?.by_direction?.to?.total_amount || 0
  const totalReceived = stats?.by_direction?.from?.total_amount || 0
  const totalAmount = totalSent + totalReceived
  const peopleCount = stats?.top_counterparties?.length || 0
  const recurringCount = stats?.top_counterparties?.filter(
    (cp) => cp.transaction_count >= 3
  ).length || 0

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 w-20 bg-muted animate-pulse rounded" />
              <div className="h-4 w-4 bg-muted animate-pulse rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-24 bg-muted animate-pulse rounded mb-1" />
              <div className="h-3 w-16 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      {/* Total P2P Volume */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total P2P</CardTitle>
          <Wallet className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatAmount(totalAmount)}</div>
          <p className="text-xs text-muted-foreground">
            {stats?.total_p2p_transactions || 0} transactions
          </p>
        </CardContent>
      </Card>

      {/* Total Sent */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Sent</CardTitle>
          <ArrowUpRight className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">
            {formatAmount(totalSent)}
          </div>
          <p className="text-xs text-muted-foreground">
            {stats?.by_direction?.to?.count || 0} outgoing
          </p>
        </CardContent>
      </Card>

      {/* Total Received */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Received</CardTitle>
          <ArrowDownLeft className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">
            {formatAmount(totalReceived)}
          </div>
          <p className="text-xs text-muted-foreground">
            {stats?.by_direction?.from?.count || 0} incoming
          </p>
        </CardContent>
      </Card>

      {/* People Count */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">People</CardTitle>
          <Users className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{peopleCount}</div>
          <p className="text-xs text-muted-foreground">
            Counterparties
          </p>
        </CardContent>
      </Card>

      {/* Recurring */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Recurring</CardTitle>
          <RefreshCw className="h-4 w-4 text-purple-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-purple-600">{recurringCount}</div>
          <p className="text-xs text-muted-foreground">
            Regular payments
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
