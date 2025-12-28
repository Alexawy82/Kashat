import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { formatAmount } from '@/app/subscriptions/lib/recurringUtils'

type SpendingByType = {
  by_type?: { type: string; count: number; monthly_total: number; annual_total: number }[]
  total_monthly?: number
  total_annual?: number
}

export function ReportsModal({
  open,
  onOpenChange,
  summary,
  spending,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  summary?: { total_monthly?: number; total_annual?: number; essential_monthly?: number; discretionary_monthly?: number }
  spending?: SpendingByType
}) {
  const byType = spending?.by_type || []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Recurring Reports</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="summary" className="space-y-4">
          <TabsList className="flex flex-wrap">
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="by-type">By Type</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="savings">Savings</TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Total monthly</div>
                <div className="text-2xl font-semibold">{formatAmount(summary?.total_monthly || 0)}</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Total annual</div>
                <div className="text-2xl font-semibold">{formatAmount(summary?.total_annual || 0)}</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Essential</div>
                <div className="text-xl font-semibold">{formatAmount(summary?.essential_monthly || 0)}</div>
              </div>
              <div className="rounded-lg border p-4">
                <div className="text-sm text-muted-foreground">Discretionary</div>
                <div className="text-xl font-semibold">{formatAmount(summary?.discretionary_monthly || 0)}</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" disabled>
                Export PDF (coming soon)
              </Button>
              <Button variant="outline" size="sm" disabled>
                Export CSV (coming soon)
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="by-type" className="space-y-3">
            {byType.length === 0 ? (
              <div className="text-sm text-muted-foreground">No type breakdown available.</div>
            ) : (
              <div className="space-y-2">
                {byType.map((row) => (
                  <div key={row.type} className="flex items-center justify-between rounded-lg border p-3">
                    <div>
                      <div className="font-medium capitalize">{row.type.replace('_', ' ')}</div>
                      <div className="text-xs text-muted-foreground">{row.count} series</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{formatAmount(row.monthly_total)}</div>
                      <Badge variant="outline" className="text-[10px]">
                        {formatAmount(row.annual_total)}/yr
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="trends">
            <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              Trends report will land after the reporting endpoints are finalized.
            </div>
          </TabsContent>

          <TabsContent value="savings">
            <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
              Savings report will surface AI optimizations and cancellations.
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
