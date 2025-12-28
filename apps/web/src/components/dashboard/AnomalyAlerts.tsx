'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { useAnomalies } from '@/hooks/useAnalytics'

const severityConfig = {
  high: { icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50', badge: 'bg-red-100 text-red-800' },
  medium: { icon: AlertCircle, color: 'text-orange-500', bg: 'bg-orange-50', badge: 'bg-orange-100 text-orange-800' },
  low: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-50', badge: 'bg-blue-100 text-blue-800' },
}

export function AnomalyAlerts() {
  const { data, isLoading, isError } = useAnomalies({ days_lookback: 14 })

  if (isLoading) return <Card className="h-48 animate-pulse bg-muted/50" />
  if (isError) return <Card className="h-48 bg-red-50 border-red-100 flex items-center justify-center text-red-500 text-sm">Error loading alerts</Card>

  const anomalies = data?.anomalies || []
  const hasAnomalies = anomalies.length > 0

  return (
    <Card className={hasAnomalies ? 'border-orange-200' : ''}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Anomaly Alerts</CardTitle>
        <AlertTriangle className={`h-4 w-4 ${hasAnomalies ? 'text-orange-500' : 'text-muted-foreground'}`} />
      </CardHeader>
      <CardContent>
        {!hasAnomalies ? (
          <div className="flex flex-col items-center justify-center h-24 text-muted-foreground">
            <Info className="h-8 w-8 mb-2 text-green-500" />
            <p className="text-sm">No anomalies detected</p>
            <p className="text-xs">Your spending looks normal</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {anomalies.slice(0, 5).map((anomaly: any, i: number) => {
              const severity = anomaly.severity || 'medium'
              const config = severityConfig[severity as keyof typeof severityConfig] || severityConfig.medium
              const Icon = config.icon

              return (
                <div key={i} className={`p-2 rounded-md ${config.bg} flex items-start gap-2`}>
                  <Icon className={`h-4 w-4 mt-0.5 ${config.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium truncate">
                        {anomaly.anomaly_type?.replace(/_/g, ' ')}
                      </span>
                      <Badge className={`text-[10px] px-1 py-0 ${config.badge}`}>
                        {severity}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {anomaly.description}
                    </p>
                    {anomaly.actual_value && (
                      <p className="text-xs font-medium">
                        ${Math.abs(anomaly.actual_value).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
