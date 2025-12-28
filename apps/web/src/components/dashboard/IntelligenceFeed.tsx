'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, TrendingUp, TrendingDown, Info, Loader2, Lightbulb, Bell } from 'lucide-react'
import { useIntelligenceFeed } from '@/hooks/useIntelligence'

const typeConfig = {
  insight: { icon: Lightbulb, color: 'text-purple-600', bg: 'bg-purple-100' },
  alert: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100' },
  notification: { icon: Bell, color: 'text-blue-600', bg: 'bg-blue-100' },
  trend: { icon: TrendingUp, color: 'text-green-600', bg: 'bg-green-100' },
}

const priorityColors = {
  urgent: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-gray-100 text-gray-800',
}

export function IntelligenceFeed() {
  const { data, isLoading, isError } = useIntelligenceFeed({
    limit: 10,
    filters: {
      include_anomalies: true,
      include_trends: true,
      include_recommendations: true,
      include_alerts: true,
      min_priority: 'low'
    }
  })

  const feedItems = data?.feed || []

  return (
    <Card className="col-span-3">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Intelligence Feed</CardTitle>
        {feedItems.length > 0 && (
          <Badge variant="secondary">{feedItems.length} items</Badge>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 className="animate-spin text-muted-foreground h-6 w-6" />
          </div>
        ) : isError ? (
          <div className="text-center p-4 text-red-500 text-sm">
            Failed to load intelligence feed
          </div>
        ) : feedItems.length === 0 ? (
          <div className="text-center p-8 text-muted-foreground">
            <Info className="h-8 w-8 mx-auto mb-2 text-green-500" />
            <p className="text-sm">All caught up!</p>
            <p className="text-xs">No new insights or alerts</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
            {feedItems.map((item: any, i: number) => {
              const config = typeConfig[item.type as keyof typeof typeConfig] || typeConfig.notification
              const Icon = config.icon
              const priorityClass = priorityColors[item.priority as keyof typeof priorityColors] || priorityColors.low

              return (
                <div
                  key={i}
                  className="flex items-start gap-3 p-3 border rounded-lg bg-card hover:bg-accent/50 transition-colors cursor-pointer"
                >
                  <div className={`p-2 rounded-full ${config.bg}`}>
                    <Icon className={`h-4 w-4 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-sm truncate">{item.title}</h4>
                      <Badge className={`text-[10px] px-1.5 py-0 ${priorityClass}`}>
                        {item.priority}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {item.description}
                    </p>
                    {item.data?.recommendations?.[0] && (
                      <p className="text-xs text-primary mt-1 flex items-center gap-1">
                        <Lightbulb className="h-3 w-3" />
                        {item.data.recommendations[0]}
                      </p>
                    )}
                    {item.subtype && (
                      <Badge variant="outline" className="text-[10px] mt-2">
                        {item.subtype}
                      </Badge>
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