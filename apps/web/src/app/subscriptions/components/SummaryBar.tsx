import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DollarSign, ShieldCheck, Sparkles, Wallet, AlertTriangle } from 'lucide-react'
import { formatAmount } from '@/app/subscriptions/lib/recurringUtils'

export type RecurringSummary = {
  total_monthly?: number
  essential_monthly?: number
  discretionary_monthly?: number
  total_annual?: number
}

export function SummaryBar({
  summary,
  pendingCount,
  isLoading,
}: {
  summary?: RecurringSummary
  pendingCount: number
  isLoading?: boolean
}) {
  const loading = isLoading && !summary

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Monthly Total</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {loading ? '—' : formatAmount(summary?.total_monthly || 0)}
          </div>
          <div className="text-xs text-muted-foreground">All recurring spend</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Essential</CardTitle>
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {loading ? '—' : formatAmount(summary?.essential_monthly || 0)}
          </div>
          <div className="text-xs text-muted-foreground">Must-pay charges</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Discretionary</CardTitle>
          <Sparkles className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {loading ? '—' : formatAmount(summary?.discretionary_monthly || 0)}
          </div>
          <div className="text-xs text-muted-foreground">Optional services</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Annual Total</CardTitle>
          <Wallet className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {loading ? '—' : formatAmount(summary?.total_annual || 0)}
          </div>
          <div className="text-xs text-muted-foreground">12-month projection</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{pendingCount}</div>
          <div className="text-xs text-muted-foreground">
            <Badge variant="outline" className="text-[10px]">
              {pendingCount === 1 ? '1 candidate' : `${pendingCount} candidates`}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
