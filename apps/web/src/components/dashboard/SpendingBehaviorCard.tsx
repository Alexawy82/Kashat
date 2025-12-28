'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { User, AlertTriangle } from 'lucide-react'
import { useSpendingBehavior } from '@/hooks/useIntelligence'

const personaColors: Record<string, string> = {
  'saver': 'bg-green-100 text-green-800',
  'balanced': 'bg-blue-100 text-blue-800',
  'spender': 'bg-orange-100 text-orange-800',
  'investor': 'bg-purple-100 text-purple-800',
}

export function SpendingBehaviorCard() {
  const { data, isLoading, isError } = useSpendingBehavior()

  if (isLoading) return <Card className="h-40 animate-pulse bg-muted/50" />
  if (isError) return <Card className="h-40 bg-red-50 border-red-100 flex items-center justify-center text-red-500 text-sm">Error loading behavior</Card>

  const profile = data?.behavior_profile
  const persona = profile?.persona || 'balanced'
  const volatility = profile?.spending_volatility || 0
  const topCategories = profile?.top_categories?.slice(0, 3) || []

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Spending Behavior</CardTitle>
        <User className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 mb-3">
          <Badge className={personaColors[persona] || 'bg-gray-100 text-gray-800'}>
            {persona.charAt(0).toUpperCase() + persona.slice(1)}
          </Badge>
          {volatility > 0.3 && (
            <Badge variant="outline" className="text-orange-600 border-orange-300">
              <AlertTriangle className="h-3 w-3 mr-1" />
              High Volatility
            </Badge>
          )}
        </div>

        {topCategories.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Top Categories:</p>
            {topCategories.map((cat: { name: string; total: number }, i: number) => (
              <div key={i} className="flex justify-between text-xs">
                <span className="text-muted-foreground">{cat.name}</span>
                <span className="font-medium">${cat.total?.toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}

        {profile?.risk_factors?.length > 0 && (
          <p className="text-xs text-orange-500 mt-2">
            {profile.risk_factors[0]}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
