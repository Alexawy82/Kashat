'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  AlertTriangle,
  TrendingUp,
  ThumbsUp,
  Loader2,
  CheckCircle,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useInsights, useRuleSuggestions } from '@/hooks/useIntelligence'
import { useCategoryCoverage } from '@/hooks/useCategories'
import { toast } from '@/components/ui/Toaster'

interface InsightAction {
  label: string
  variant: 'default' | 'destructive' | 'outline'
  onClick: () => Promise<void>
}

interface Insight {
  type: 'recommendation' | 'warning' | 'achievement' | 'opportunity'
  priority: 'high' | 'medium' | 'low'
  title: string
  description: string
  value?: number
  actions?: InsightAction[]
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export function SmartInsightsCard() {
  const router = useRouter()
  const { data: insightsData, isLoading, refetch } = useInsights({ limit: 10 })
  const { data: coverageData } = useCategoryCoverage()
  const { data: ruleSuggestions } = useRuleSuggestions({ min_occurrences: 3 })

  const [expanded, setExpanded] = useState<number | null>(null)
  const [showAll, setShowAll] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  // Transform API insights to our format
  const rawInsights = insightsData?.insights || []
  const insights: Insight[] = rawInsights.map((insight: any) => ({
    type: insight.type || 'recommendation',
    priority: insight.priority || 'medium',
    title: insight.title,
    description: insight.description,
    value: insight.potential_savings || insight.amount,
  }))

  const displayInsights = showAll ? insights : insights.slice(0, 3)
  const hasMore = insights.length > 3
  const uncategorized = coverageData?.uncategorized_count || 0
  const pendingRules = ruleSuggestions?.suggestions?.length || 0

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setRefreshing(false)
    toast.success('Insights refreshed')
  }

  const typeIcons: Record<string, React.ReactNode> = {
    recommendation: <TrendingUp className="h-4 w-4 text-blue-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-500" />,
    achievement: <ThumbsUp className="h-4 w-4 text-green-500" />,
    opportunity: <Lightbulb className="h-4 w-4 text-yellow-500" />,
  }

  const priorityColors: Record<string, string> = {
    high: 'border-l-red-500 bg-red-50/50 dark:bg-red-950/20',
    medium: 'border-l-amber-500 bg-amber-50/50 dark:bg-amber-950/20',
    low: 'border-l-blue-500',
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-500" />
            Smart Insights
            {insights.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {insights.length}
              </Badge>
            )}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            aria-label="Refresh insights"
          >
            <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Quick Stats */}
        {(uncategorized > 0 || pendingRules > 0) && (
          <div className="flex gap-2 mb-3">
            {uncategorized > 0 && (
              <Badge
                variant="outline"
                className="cursor-pointer hover:bg-accent"
                onClick={() => router.push('/transactions?uncategorized=true')}
              >
                {uncategorized} uncategorized
              </Badge>
            )}
            {pendingRules > 0 && (
              <Badge
                variant="outline"
                className="cursor-pointer hover:bg-accent"
                onClick={() => router.push('/settings/automation')}
              >
                {pendingRules} rule suggestions
              </Badge>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : displayInsights.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <CheckCircle className="h-10 w-10 mx-auto mb-2 text-green-500" />
            <p className="font-medium">All caught up!</p>
            <p className="text-sm">No new insights right now.</p>
          </div>
        ) : (
          displayInsights.map((insight, idx) => (
            <div
              key={idx}
              className={cn(
                'border-l-4 rounded-r-lg p-3 transition-colors cursor-pointer',
                priorityColors[insight.priority],
                expanded === idx ? 'bg-accent/30' : 'hover:bg-accent/20'
              )}
              onClick={() => setExpanded(expanded === idx ? null : idx)}
              role="button"
              aria-expanded={expanded === idx}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-2">
                  {typeIcons[insight.type] || typeIcons.recommendation}
                  <div className="flex-1">
                    <div className="font-medium text-sm">{insight.title}</div>
                    {insight.value && insight.value > 0 && (
                      <div className="text-sm text-muted-foreground">
                        Save {formatCurrency(insight.value)}/mo
                      </div>
                    )}
                  </div>
                </div>
                <ChevronDown
                  className={cn(
                    'h-4 w-4 transition-transform text-muted-foreground',
                    expanded === idx && 'rotate-180'
                  )}
                />
              </div>

              {expanded === idx && (
                <div className="mt-3 space-y-3">
                  <p className="text-sm text-muted-foreground">{insight.description}</p>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        toast.success('Insight dismissed')
                        // Would call dismiss API here
                      }}
                    >
                      <X className="h-3 w-3 mr-1" /> Dismiss
                    </Button>
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        // Navigate to relevant page based on insight type
                        router.push('/transactions')
                      }}
                    >
                      Take Action
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {/* View All / Show Less */}
        {hasMore && (
          <Button
            variant="ghost"
            className="w-full mt-2"
            onClick={() => setShowAll(!showAll)}
          >
            {showAll ? (
              <>
                Show Less <ChevronUp className="h-4 w-4 ml-1" />
              </>
            ) : (
              <>
                View All ({insights.length}) <ChevronDown className="h-4 w-4 ml-1" />
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
