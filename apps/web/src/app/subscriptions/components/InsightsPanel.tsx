'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sparkles, ShieldAlert, TrendingDown, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { formatAmount } from '@/app/subscriptions/lib/recurringUtils'

function InsightItem({
  title,
  description,
  tag,
  onClick,
  actionLabel,
}: {
  title: string
  description: string
  tag?: string
  onClick?: () => void
  actionLabel?: string
}) {
  return (
    <div
      className={`space-y-1 rounded-lg border border-border/60 bg-muted/30 p-3 ${
        onClick ? 'cursor-pointer hover:bg-muted/50 transition-colors' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">{title}</p>
        <div className="flex items-center gap-2">
          {tag && (
            <Badge variant="outline" className="text-[10px]">
              {tag}
            </Badge>
          )}
          {onClick && <ExternalLink className="h-3 w-3 text-muted-foreground" />}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{description}</p>
      {actionLabel && onClick && (
        <Button variant="link" size="sm" className="h-auto p-0 text-xs text-primary">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

interface ExpandableSectionProps {
  title: string
  icon: React.ReactNode
  items: any[]
  defaultShow: number
  renderItem: (item: any, index: number) => React.ReactNode
  emptyMessage: string
}

function ExpandableSection({
  title,
  icon,
  items,
  defaultShow,
  renderItem,
  emptyMessage,
}: ExpandableSectionProps) {
  const [expanded, setExpanded] = useState(false)
  const displayItems = expanded ? items : items.slice(0, defaultShow)
  const hasMore = items.length > defaultShow

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold">
          {icon}
          {title}
          {items.length > 0 && (
            <Badge variant="secondary" className="text-[10px]">
              {items.length}
            </Badge>
          )}
        </div>
        {hasMore && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                Show Less <ChevronUp className="ml-1 h-3 w-3" />
              </>
            ) : (
              <>
                View All <ChevronDown className="ml-1 h-3 w-3" />
              </>
            )}
          </Button>
        )}
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">{emptyMessage}</p>
      ) : (
        displayItems.map(renderItem)
      )}
    </div>
  )
}

export function InsightsPanel({
  insights,
  optimizations,
  risks,
  isLoading,
  onSeriesClick,
}: {
  insights: any[] | any
  optimizations: any[] | any
  risks: any[] | any
  isLoading?: boolean
  onSeriesClick?: (seriesId: string) => void
}) {
  // Ensure we always have arrays (API may return {error: ...} object on failure)
  const insightsList = Array.isArray(insights) ? insights : []
  const optimizationsList = Array.isArray(optimizations) ? optimizations : []
  const risksList = Array.isArray(risks) ? risks : []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="h-5 w-5 text-amber-500" />
          AI Insights
        </CardTitle>
        <CardDescription>Actionable ways to save, optimize, and reduce risk.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading insights…</div>
        ) : (
          <div className="grid gap-4">
            <ExpandableSection
              title="Highlights"
              icon={<Sparkles className="h-4 w-4 text-amber-500" />}
              items={insightsList}
              defaultShow={3}
              emptyMessage="No insights yet."
              renderItem={(item) => {
                const seriesId = item.action_series_id || item.series_id || item.data?.series_id
                return (
                  <InsightItem
                    key={item.id}
                    title={item.title || 'Insight'}
                    description={item.message || ''}
                    tag={item.action_label || item.type}
                    onClick={seriesId && onSeriesClick ? () => onSeriesClick(seriesId) : undefined}
                    actionLabel={item.actionable ? item.action_label : undefined}
                  />
                )
              }}
            />

            <ExpandableSection
              title="Savings"
              icon={<TrendingDown className="h-4 w-4 text-green-600" />}
              items={optimizationsList}
              defaultShow={2}
              emptyMessage="No savings opportunities yet."
              renderItem={(item) => (
                <InsightItem
                  key={item.id}
                  title={item.title}
                  description={`${item.description || ''} Save ${formatAmount(item.potential_annual_savings || 0)}/yr.`}
                  tag={item.category}
                  onClick={item.series_id && onSeriesClick ? () => onSeriesClick(item.series_id) : undefined}
                  actionLabel="View Details"
                />
              )}
            />

            <ExpandableSection
              title="Cancellation Risks"
              icon={<ShieldAlert className="h-4 w-4 text-red-500" />}
              items={risksList}
              defaultShow={2}
              emptyMessage="No risk alerts right now."
              renderItem={(item) => (
                <InsightItem
                  key={item.series_id || item.merchant}
                  title={item.merchant || 'Risk'}
                  description={item.recommendation || 'Review this charge.'}
                  tag={item.risk_level}
                  onClick={item.series_id && onSeriesClick ? () => onSeriesClick(item.series_id) : undefined}
                  actionLabel="Review"
                />
              )}
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
