'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ChevronRight, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { HealthScoreModal } from '../modals/HealthScoreModal'

interface HealthComponents {
  spending_health?: number
  savings_health?: number
  budgeting_health?: number
  trend_health?: number
}

interface HeroHealthScoreProps {
  score: number
  grade: string
  components?: HealthComponents
  strengths?: string[]
  improvements?: string[]
  recommendations?: string[]
  isLoading?: boolean
}

export function HeroHealthScore({
  score,
  grade,
  components,
  strengths = [],
  improvements = [],
  recommendations = [],
  isLoading,
}: HeroHealthScoreProps) {
  const [modalOpen, setModalOpen] = useState(false)

  if (isLoading) {
    return (
      <Card className="h-[120px] flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </Card>
    )
  }

  const gradeColors: Record<string, string> = {
    A: 'text-green-600 dark:text-green-400',
    B: 'text-blue-600 dark:text-blue-400',
    C: 'text-yellow-600 dark:text-yellow-400',
    D: 'text-orange-600 dark:text-orange-400',
    F: 'text-red-600 dark:text-red-400',
  }

  const progressColor =
    score >= 80
      ? '[&>div]:bg-green-500'
      : score >= 60
        ? '[&>div]:bg-yellow-500'
        : '[&>div]:bg-red-500'

  return (
    <>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Card
              className="cursor-pointer hover:bg-accent/50 transition-all hover:shadow-md active:scale-[0.99]"
              onClick={() => setModalOpen(true)}
              role="button"
              aria-label="View health score breakdown"
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground font-medium">Financial Health</span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>

                <div className="flex items-baseline gap-2 mt-2">
                  <span className={cn('text-3xl font-bold', gradeColors[grade] || 'text-gray-600')}>
                    {grade}
                  </span>
                  <span className="text-muted-foreground text-sm">{score}/100</span>
                </div>

                <Progress value={score} className={cn('mt-3 h-2', progressColor)} />

                <div className="mt-2 text-xs text-muted-foreground">
                  Click for breakdown & tips
                </div>
              </CardContent>
            </Card>
          </TooltipTrigger>
          <TooltipContent>
            <p>Click for score breakdown and improvement tips</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <HealthScoreModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        score={score}
        grade={grade}
        components={components}
        strengths={strengths}
        improvements={improvements}
        recommendations={recommendations}
      />
    </>
  )
}
