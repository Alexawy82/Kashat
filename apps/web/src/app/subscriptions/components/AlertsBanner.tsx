import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertCircle, AlertTriangle, TrendingUp, ChevronRight } from 'lucide-react'

interface AlertItem {
  id?: string
  series_id?: string
  merchant_name?: string
  merchant?: string
  date?: string
}

function getMerchantDisplay(item: AlertItem): string {
  return item.merchant_name || item.merchant || 'Unknown'
}

function ClickableItems({
  items,
  maxDisplay,
  colorClass,
  onItemClick,
}: {
  items: AlertItem[]
  maxDisplay: number
  colorClass: string
  onItemClick?: (item: AlertItem) => void
}) {
  const displayItems = items.slice(0, maxDisplay)
  const remaining = items.length - maxDisplay

  return (
    <span className={colorClass}>
      {displayItems.map((item, idx) => (
        <span key={item.id || item.series_id || idx}>
          {onItemClick ? (
            <button
              onClick={() => onItemClick(item)}
              className="hover:underline cursor-pointer font-medium"
            >
              {getMerchantDisplay(item)}
            </button>
          ) : (
            getMerchantDisplay(item)
          )}
          {idx < displayItems.length - 1 && ', '}
        </span>
      ))}
      {remaining > 0 && (
        <Button
          variant="link"
          size="sm"
          className={`${colorClass} p-0 h-auto ml-1`}
          onClick={() => onItemClick?.(items[maxDisplay])}
        >
          +{remaining} more <ChevronRight className="h-3 w-3" />
        </Button>
      )}
    </span>
  )
}

export function AlertsBanner({
  overdueItems,
  dueSoonItems,
  priceHikeItems,
  onItemClick,
}: {
  overdueItems: AlertItem[]
  dueSoonItems: AlertItem[]
  priceHikeItems: AlertItem[]
  onItemClick?: (item: AlertItem) => void
}) {
  if (overdueItems.length === 0 && dueSoonItems.length === 0 && priceHikeItems.length === 0) return null

  return (
    <Alert className="border-amber-200 bg-amber-50/60">
      <AlertDescription className="space-y-2">
        {overdueItems.length > 0 && (
          <div className="flex items-start gap-2 text-sm">
            <Badge variant="outline" className="border-red-300 text-red-700 text-[10px]">
              <AlertCircle className="h-3 w-3 mr-1" />
              Overdue
            </Badge>
            <ClickableItems
              items={overdueItems}
              maxDisplay={3}
              colorClass="text-red-700"
              onItemClick={onItemClick}
            />
          </div>
        )}
        {dueSoonItems.length > 0 && (
          <div className="flex items-start gap-2 text-sm">
            <Badge variant="outline" className="border-yellow-300 text-yellow-800 text-[10px]">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Due Soon
            </Badge>
            <ClickableItems
              items={dueSoonItems}
              maxDisplay={4}
              colorClass="text-yellow-800"
              onItemClick={onItemClick}
            />
          </div>
        )}
        {priceHikeItems.length > 0 && (
          <div className="flex items-start gap-2 text-sm">
            <Badge variant="outline" className="border-orange-300 text-orange-700 text-[10px]">
              <TrendingUp className="h-3 w-3 mr-1" />
              Price Hikes
            </Badge>
            <ClickableItems
              items={priceHikeItems}
              maxDisplay={4}
              colorClass="text-orange-700"
              onItemClick={onItemClick}
            />
          </div>
        )}
      </AlertDescription>
    </Alert>
  )
}
