'use client'

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Sparkles,
  Brain,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle2,
  Zap,
  ArrowRight,
  Loader2
} from 'lucide-react'
import { useInsights, useRuleSuggestions } from '@/hooks/useIntelligence'
import { useCategoryCoverage, useAISuccessMetrics, useCategorizeAllTransactions, useIsCategorizationRunning } from '@/hooks/useCategories'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'
import { AnimatedCount, AnimatedPercentage } from '@/components/ui/AnimatedNumber'
import { toast } from '@/components/ui/Toaster'
import Link from 'next/link'

interface Insight {
  type: 'recommendation' | 'warning' | 'achievement' | 'opportunity'
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  action_url?: string
  action_label?: string
}

export function AIInsightsWidget() {
  const { data: insightsData, isLoading: insightsLoading } = useInsights({ limit: 5 })
  const { data: coverageData, isLoading: coverageLoading } = useCategoryCoverage()
  const { data: metricsData } = useAISuccessMetrics()
  const { data: ruleSuggestions } = useRuleSuggestions({ min_occurrences: 3 })
  const categorizeAll = useCategorizeAllTransactions()
  const isRunning = useIsCategorizationRunning()

  const insights: Insight[] = insightsData?.insights || []
  const coverage = coverageData?.coverage_percent || 0
  const uncategorized = coverageData?.uncategorized_count || 0
  const accuracy = metricsData?.accuracy_rate || 0
  const pendingRules = ruleSuggestions?.suggestions?.length || 0

  const handleAutoCategorize = async () => {
    try {
      const result = await categorizeAll.mutateAsync({ batch_size: 50 })
      if (result.status === 'started') {
        toast.success('AI categorization started', {
          description: `Processing ${result.total_transactions} transactions...`
        })
      } else if (result.status === 'no_work') {
        toast.info('All transactions are already categorized')
      }
    } catch {
      toast.error('Failed to start categorization')
    }
  }

  if (insightsLoading || coverageLoading) {
    return <CardSkeleton className="lg:col-span-2" />
  }

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />
              AI Insights
              <Badge variant="secondary" className="text-xs">Beta</Badge>
            </CardTitle>
            <CardDescription>
              AI-powered recommendations and automation status
            </CardDescription>
          </div>
          {uncategorized > 0 && (
            <Button
              size="sm"
              onClick={handleAutoCategorize}
              disabled={isRunning || categorizeAll.isPending}
            >
              {isRunning || categorizeAll.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  Auto-Categorize ({uncategorized})
                </>
              )}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* AI Stats Row */}
        <div className="grid gap-4 md:grid-cols-3">
          {/* Category Coverage */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Category Coverage</span>
              <AnimatedPercentage
                value={coverage}
                className={`font-semibold ${
                  coverage >= 90 ? 'text-green-600 dark:text-green-400' :
                  coverage >= 70 ? 'text-yellow-600 dark:text-yellow-400' :
                  'text-red-600 dark:text-red-400'
                }`}
              />
            </div>
            <Progress value={coverage} className="h-2" />
          </div>

          {/* AI Accuracy */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">AI Accuracy</span>
              <AnimatedPercentage
                value={accuracy * 100}
                className="font-semibold text-primary"
              />
            </div>
            <Progress value={accuracy * 100} className="h-2" />
          </div>

          {/* Pending Rules */}
          <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <span className="text-sm text-muted-foreground">Suggested Rules</span>
            </div>
            <div className="flex items-center gap-2">
              <AnimatedCount value={pendingRules} className="font-semibold" />
              {pendingRules > 0 && (
                <Link href="/settings/automation">
                  <Button variant="ghost" size="sm" className="h-6 px-2">
                    <ArrowRight className="h-3 w-3" />
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Insights List */}
        {insights.length > 0 ? (
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Recommendations</h4>
            {insights.slice(0, 4).map((insight, i) => (
              <InsightCard key={i} insight={insight} />
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-muted-foreground">
            <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500" />
            <p className="text-sm">All caught up! No new insights.</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function InsightCard({ insight }: { insight: Insight }) {
  const iconMap = {
    recommendation: <TrendingUp className="h-4 w-4 text-blue-500" />,
    warning: <AlertCircle className="h-4 w-4 text-yellow-500" />,
    achievement: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    opportunity: <Sparkles className="h-4 w-4 text-purple-500" />,
  }

  const priorityColors = {
    high: 'border-l-red-500',
    medium: 'border-l-yellow-500',
    low: 'border-l-blue-500',
  }

  return (
    <div
      className={`flex items-start gap-3 p-3 bg-muted/30 dark:bg-muted/20 rounded-lg border-l-4 ${priorityColors[insight.priority]}`}
    >
      <div className="mt-0.5">{iconMap[insight.type]}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{insight.title}</p>
        <p className="text-xs text-muted-foreground line-clamp-2">
          {insight.description}
        </p>
        {insight.action_url && (
          <Link href={insight.action_url}>
            <Button variant="link" size="sm" className="h-auto p-0 text-xs mt-1">
              {insight.action_label || 'Take action'} <ArrowRight className="ml-1 h-3 w-3" />
            </Button>
          </Link>
        )}
      </div>
    </div>
  )
}
