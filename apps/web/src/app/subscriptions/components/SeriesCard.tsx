import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { AlertCircle, CheckCircle2, TrendingUp, XCircle } from 'lucide-react'
import {
  formatAmount,
  getAmountVariance,
  getCadenceLabel,
  getMerchantName,
  RecurringSeries,
} from '@/app/subscriptions/lib/recurringUtils'

function StatusBadge({ status, daysOverdue }: { status: string; daysOverdue?: number | null }) {
  if (status === 'active') {
    return (
      <Badge variant="outline" className="text-green-600 border-green-300 text-[10px]">
        <CheckCircle2 className="h-3 w-3 mr-0.5" />
        Active
      </Badge>
    )
  }
  if (status === 'overdue') {
    return (
      <Badge variant="outline" className="text-red-600 border-red-300 bg-red-50 text-[10px]">
        <AlertCircle className="h-3 w-3 mr-0.5" />
        {daysOverdue ? `${daysOverdue}d overdue` : 'Overdue'}
      </Badge>
    )
  }
  if (status === 'likely_cancelled') {
    return (
      <Badge variant="outline" className="text-gray-500 border-gray-300 text-[10px]">
        <XCircle className="h-3 w-3 mr-0.5" />
        Likely cancelled
      </Badge>
    )
  }
  return null
}

export function SeriesCard({ item, onSelect }: { item: RecurringSeries; onSelect?: (item: RecurringSeries) => void }) {
  const amount = Math.abs(item.amount_mean || item.amount || 0)
  const variance = getAmountVariance(item)
  const isVariable = amount > 0 && variance > 0.15
  const isOverdue = item.status === 'overdue' || item.status === 'likely_cancelled'

  return (
    <Card
      className={`transition ${isOverdue ? 'border-red-200 bg-red-50/40' : 'bg-muted/30'} ${
        onSelect ? 'cursor-pointer hover:border-primary/40' : ''
      }`}
      onClick={onSelect ? () => onSelect(item) : undefined}
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onKeyDown={
        onSelect
          ? (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onSelect(item)
              }
            }
          : undefined
      }
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium truncate">{getMerchantName(item)}</span>
              {item.status && item.status !== 'unknown' && (
                <StatusBadge status={item.status} daysOverdue={item.days_overdue} />
              )}
              {item.price_hike && (
                <Badge variant="outline" className="border-orange-300 text-orange-600 text-[10px]">
                  <TrendingUp className="h-3 w-3 mr-0.5" />
                  PRICE HIKE
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1 flex-wrap text-xs text-muted-foreground">
              <Badge variant="secondary" className="text-[10px]">
                {getCadenceLabel(item)}
              </Badge>
              {item.category_name && (
                <Badge variant="outline" className="text-[10px]">
                  {item.category_name}
                </Badge>
              )}
              <span>Next: {item.next_date || '—'}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="font-semibold">{formatAmount(amount)}</div>
            {isVariable ? (
              <div className="text-[10px] text-muted-foreground">Variable</div>
            ) : (
              <div className="text-[10px] text-muted-foreground">Fixed</div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
