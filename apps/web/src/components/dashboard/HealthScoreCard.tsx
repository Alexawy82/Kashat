'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, TrendingUp, TrendingDown } from 'lucide-react'
import { useFinancialHealth } from '@/hooks/useIntelligence'
import { AnimatedCount } from '@/components/ui/AnimatedNumber'
import { CardSkeleton } from '@/components/ui/LoadingSpinner'

const gradeColors: Record<string, string> = {
  'A': 'text-green-600 dark:text-green-400',
  'B': 'text-green-500 dark:text-green-400',
  'C': 'text-yellow-500 dark:text-yellow-400',
  'D': 'text-orange-500 dark:text-orange-400',
  'F': 'text-red-500 dark:text-red-400',
}

export function HealthScoreCard() {
  const { data, isLoading, isError } = useFinancialHealth()

  if (isLoading) return <CardSkeleton className="h-40" />
  if (isError) return <Card className="h-40 bg-destructive/10 border-destructive/20 dark:bg-destructive/20 flex items-center justify-center text-destructive text-sm">Error loading health</Card>

  const report = data?.health_report
  const score = report?.overall_score ?? 0
  const grade = report?.health_grade ?? 'C'
  const scoreColor = score >= 80 ? 'text-green-600 dark:text-green-400' : score >= 60 ? 'text-yellow-500 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Financial Health</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <AnimatedCount
            value={score}
            duration={800}
            className={`text-4xl font-bold tracking-tighter ${scoreColor}`}
          />
          <span className={`text-2xl font-semibold ${gradeColors[grade] || 'text-gray-500'}`}>
            {grade}
          </span>
        </div>
        {report?.key_strengths?.[0] && (
          <p className="text-xs text-green-600 dark:text-green-400 mt-2 flex items-center gap-1">
            <TrendingUp className="h-3 w-3" aria-hidden="true" />
            {report.key_strengths[0]}
          </p>
        )}
        {report?.improvement_areas?.[0] && (
          <p className="text-xs text-orange-500 dark:text-orange-400 mt-1 flex items-center gap-1">
            <TrendingDown className="h-3 w-3" aria-hidden="true" />
            {report.improvement_areas[0]}
          </p>
        )}
      </CardContent>
    </Card>
  )
}