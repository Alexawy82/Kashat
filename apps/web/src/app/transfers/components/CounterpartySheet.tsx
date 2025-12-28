"use client"

import { useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  User,
  Building2,
  RefreshCw,
  GitMerge,
  ExternalLink,
  Loader2,
  ArrowUpRight,
  ArrowDownLeft,
} from "lucide-react"
import Link from "next/link"
import type { Counterparty } from "@/hooks/useP2P"
import { useCounterpartyTransactions } from "@/hooks/useP2P"

interface CounterpartySheetProps {
  counterparty: Counterparty | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onMerge?: (counterparty: Counterparty) => void
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(Math.abs(amount))
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-"
  const date = new Date(dateStr)
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

export function CounterpartySheet({
  counterparty,
  open,
  onOpenChange,
  onMerge,
}: CounterpartySheetProps) {
  const { data: transactions, isLoading: txLoading } = useCounterpartyTransactions(
    open ? counterparty?.id ?? null : null
  )

  if (!counterparty) return null

  const isRecurring = counterparty.is_recurring || counterparty.transaction_count >= 3
  const netFlow = counterparty.total_received - counterparty.total_sent
  const isBusiness = counterparty.name.toUpperCase() === counterparty.name &&
    counterparty.name.length > 3 &&
    !counterparty.name.includes(" ")

  // Calculate average per transaction
  const avgAmount = counterparty.transaction_count > 0
    ? (counterparty.total_sent + counterparty.total_received) / counterparty.transaction_count
    : 0

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="space-y-4">
          {/* Header with icon and name */}
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-full ${isBusiness ? "bg-blue-100" : "bg-slate-100"}`}>
              {isBusiness ? (
                <Building2 className="h-6 w-6 text-blue-600" />
              ) : (
                <User className="h-6 w-6 text-slate-600" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-xl truncate">{counterparty.name}</SheetTitle>
              <SheetDescription className="flex items-center gap-2 mt-1">
                <Badge variant="outline">{isBusiness ? "Business" : "Person"}</Badge>
                {isRecurring && (
                  <Badge variant="secondary" className="gap-1">
                    <RefreshCw className="h-3 w-3" />
                    Recurring
                  </Badge>
                )}
              </SheetDescription>
            </div>
          </div>

          {/* Aliases */}
          {counterparty.aliases && counterparty.aliases.length > 0 && (
            <div className="bg-muted/50 rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-1">Also known as:</div>
              <div className="flex flex-wrap gap-1">
                {counterparty.aliases.map((alias, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {alias}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </SheetHeader>

        <Separator className="my-6" />

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-red-600">
                {formatAmount(counterparty.total_sent)}
              </div>
              <div className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                <ArrowUpRight className="h-3 w-3" />
                Total Sent
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-green-600">
                {formatAmount(counterparty.total_received)}
              </div>
              <div className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                <ArrowDownLeft className="h-3 w-3" />
                Total Received
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Additional Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6 text-center">
          <div>
            <div className={`text-lg font-bold ${netFlow >= 0 ? "text-green-600" : "text-red-600"}`}>
              {netFlow >= 0 ? "+" : ""}{formatAmount(netFlow)}
            </div>
            <div className="text-xs text-muted-foreground">Net Flow</div>
          </div>
          <div>
            <div className="text-lg font-bold">{counterparty.transaction_count}</div>
            <div className="text-xs text-muted-foreground">Transactions</div>
          </div>
          <div>
            <div className="text-lg font-bold">{formatAmount(avgAmount)}</div>
            <div className="text-xs text-muted-foreground">Avg Amount</div>
          </div>
        </div>

        {/* Date Range */}
        <div className="flex justify-between text-sm text-muted-foreground mb-6 bg-muted/30 rounded-lg p-3">
          <div>
            <span className="text-foreground font-medium">First: </span>
            {formatDate(counterparty.first_seen)}
          </div>
          <div>
            <span className="text-foreground font-medium">Last: </span>
            {formatDate(counterparty.last_seen)}
          </div>
        </div>

        <Separator className="my-6" />

        {/* Actions */}
        <div className="space-y-2 mb-6">
          <div className="text-sm font-medium mb-3">Actions</div>
          <div className="grid grid-cols-2 gap-2">
            {onMerge && (
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => onMerge(counterparty)}
              >
                <GitMerge className="h-4 w-4" />
                Merge with...
              </Button>
            )}
            <Button variant="outline" className="gap-2" asChild>
              <Link href={`/transactions?q=${encodeURIComponent(counterparty.name)}`}>
                <ExternalLink className="h-4 w-4" />
                View All Transactions
              </Link>
            </Button>
          </div>
        </div>

        <Separator className="my-6" />

        {/* Recent Transactions */}
        <div>
          <div className="text-sm font-medium mb-3">Recent Transactions</div>
          {txLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !transactions || transactions.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-8">
              No transactions found
            </div>
          ) : (
            <div className="space-y-2">
              {transactions.slice(0, 10).map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-xs text-muted-foreground">
                      {formatDate(tx.posted_at)}
                    </div>
                    <div className="text-sm truncate">{tx.description_norm}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-[10px]">
                        {tx.service}
                      </Badge>
                      {tx.transaction_type && tx.transaction_type !== "unknown" && (
                        <Badge variant="secondary" className="text-[10px]">
                          {tx.transaction_type.replace("_", " ")}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div
                    className={`text-sm font-medium ${
                      tx.direction === "from" ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {tx.direction === "from" ? "+" : "-"}
                    {formatAmount(tx.amount)}
                  </div>
                </div>
              ))}
              {transactions.length > 10 && (
                <div className="text-xs text-muted-foreground text-center pt-2">
                  Showing 10 of {transactions.length} transactions
                </div>
              )}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
