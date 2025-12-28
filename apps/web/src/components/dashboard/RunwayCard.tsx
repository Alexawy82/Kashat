'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Hourglass, AlertTriangle } from 'lucide-react'
import { useCashflowProjection } from '@/hooks/useAnalytics'

export function RunwayCard() {
  const { data, isLoading, isError } = useCashflowProjection({ forecast_months: 6 })

  if (isLoading) return <Card className="h-40 animate-pulse bg-muted/50" />
  if (isError) return (
    <Card className="h-40 bg-red-50 border-red-100 flex items-center justify-center text-red-500 text-sm">
      Error loading runway
    </Card>
  )

  // Calculate runway days from months (approximate 30 days/month)
  const runwayMonths = data?.runway_months ?? 0
  const runwayDays = Math.round(runwayMonths * 30)

  // Calculate projected date
  const projectedDate = new Date()
  projectedDate.setMonth(projectedDate.getMonth() + Math.floor(runwayMonths))
  const dateStr = projectedDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })

  // Calculate progress bar width (cap at 100%)
  const progressPercent = Math.min(100, Math.max(0, (runwayMonths / 12) * 100))

  // Determine status color
  const isLow = runwayMonths < 3
  const isMedium = runwayMonths >= 3 && runwayMonths < 6

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Runway</CardTitle>
        <Hourglass className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-5xl font-bold tracking-tighter ${isLow ? 'text-red-600' : isMedium ? 'text-yellow-600' : 'text-blue-600'}`}>
          {runwayDays > 0 ? runwayDays : '--'}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {runwayDays > 0 ? 'Days left at current burn rate' : 'Insufficient data for projection'}
        </p>
        {runwayDays > 0 && (
          <>
            <div className="mt-4 h-2 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full ${isLow ? 'bg-red-500' : isMedium ? 'bg-yellow-500' : 'bg-blue-500'}`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Projected until {dateStr}
            </p>
          </>
        )}
        {isLow && runwayDays > 0 && (
          <div className="flex items-center gap-1 mt-2 text-xs text-red-600">
            <AlertTriangle className="h-3 w-3" />
            Low runway warning
          </div>
        )}
      </CardContent>
    </Card>
  )
}