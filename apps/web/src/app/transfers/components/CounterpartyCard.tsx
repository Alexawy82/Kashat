"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  User,
  Building2,
  RefreshCw,
  ChevronRight,
} from "lucide-react"
import type { Counterparty } from "@/hooks/useP2P"

// Service icons/colors
const SERVICE_COLORS: Record<string, string> = {
  zelle: "bg-purple-100 text-purple-700",
  venmo: "bg-blue-100 text-blue-700",
  cashapp: "bg-green-100 text-green-700",
  paypal: "bg-indigo-100 text-indigo-700",
  wire: "bg-orange-100 text-orange-700",
  western_union: "bg-yellow-100 text-yellow-700",
}

interface CounterpartyCardProps {
  counterparty: Counterparty
  onClick: () => void
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-"
  const date = new Date(dateStr)
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export function CounterpartyCard({ counterparty, onClick }: CounterpartyCardProps) {
  const isRecurring = counterparty.is_recurring || counterparty.transaction_count >= 3
  const netFlow = counterparty.total_received - counterparty.total_sent
  const netPositive = netFlow > 0

  // Determine if this looks like a business (simple heuristic)
  const isBusiness = counterparty.name.toUpperCase() === counterparty.name &&
    counterparty.name.length > 3 &&
    !counterparty.name.includes(" ")

  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-all hover:border-primary/50"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Icon + Name + Type */}
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className={`p-2 rounded-full ${isBusiness ? "bg-blue-100" : "bg-slate-100"}`}>
              {isBusiness ? (
                <Building2 className="h-5 w-5 text-blue-600" />
              ) : (
                <User className="h-5 w-5 text-slate-600" />
              )}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate">{counterparty.name}</span>
                {counterparty.aliases && counterparty.aliases.length > 0 && (
                  <Badge variant="outline" className="text-[10px] shrink-0">
                    +{counterparty.aliases.length} alias
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{isBusiness ? "Business" : "Person"}</span>
                {isRecurring && (
                  <>
                    <span>•</span>
                    <span className="flex items-center gap-1 text-purple-600">
                      <RefreshCw className="h-3 w-3" />
                      Recurring
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Center: Amounts */}
          <div className="text-right shrink-0">
            <div className="flex items-center gap-4">
              <div>
                <div className="text-sm font-semibold text-red-600">
                  {formatAmount(counterparty.total_sent)}
                </div>
                <div className="text-[10px] text-muted-foreground">sent</div>
              </div>
              <div>
                <div className="text-sm font-semibold text-green-600">
                  {formatAmount(counterparty.total_received)}
                </div>
                <div className="text-[10px] text-muted-foreground">received</div>
              </div>
            </div>
          </div>

          {/* Right: Stats + Arrow */}
          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <div className="text-sm font-medium">
                {counterparty.transaction_count} tx
              </div>
              <div className="text-[10px] text-muted-foreground">
                Last: {formatDate(counterparty.last_seen)}
              </div>
            </div>
            <div className={`text-right px-2 py-1 rounded ${netPositive ? "bg-green-50" : "bg-red-50"}`}>
              <div className={`text-sm font-bold ${netPositive ? "text-green-600" : "text-red-600"}`}>
                {netPositive ? "+" : ""}{formatAmount(netFlow)}
              </div>
              <div className="text-[10px] text-muted-foreground">net</div>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
