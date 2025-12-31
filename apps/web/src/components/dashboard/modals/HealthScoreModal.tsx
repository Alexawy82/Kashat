'use client'

import { useRouter } from 'next/navigation'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  TrendingUp,
  TrendingDown,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface HealthComponent {
  name: string
  score: number
  label: string
  description?: string
}

interface HealthScoreModalProps {
  open: boolean
  onClose: () => void
  score: number
  grade: string
  components?: {
    spending_health?: number
    savings_health?: number
    budgeting_health?: number
    trend_health?: number
  }
  strengths?: string[]
  improvements?: string[]
  recommendations?: string[]
}

const componentLabels: Record<string, { label: string; icon: React.ReactNode }> = {
  spending_health: { label: 'Spending Health', icon: <TrendingDown className="h-4 w-4" /> },
  savings_health: { label: 'Savings Health', icon: <TrendingUp className="h-4 w-4" /> },
  budgeting_health: { label: 'Budgeting', icon: <CheckCircle className="h-4 w-4" /> },
  trend_health: { label: 'Trends', icon: <TrendingUp className="h-4 w-4" /> },
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

function getProgressColor(score: number): string {
  if (score >= 80) return '[&>div]:bg-green-500'
  if (score >= 60) return '[&>div]:bg-yellow-500'
  return '[&>div]:bg-red-500'
}

export function HealthScoreModal({
  open,
  onClose,
  score,
  grade,
  components,
  strengths = [],
  improvements = [],
  recommendations = [],
}: HealthScoreModalProps) {
  const router = useRouter()

  const componentList: HealthComponent[] = components
    ? Object.entries(components).map(([key, value]) => ({
        name: key,
        score: value,
        label: componentLabels[key]?.label || key,
      }))
    : []

  const gradeColors: Record<string, string> = {
    A: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    B: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    D: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    F: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Financial Health Score</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Overall Score */}
          <div className="text-center py-4">
            <div className="flex items-center justify-center gap-3">
              <span className={cn('text-5xl font-bold', getScoreColor(score))}>{score}</span>
              <Badge className={cn('text-xl px-3 py-1', gradeColors[grade] || gradeColors.C)}>
                {grade}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              {score >= 80 ? 'Excellent financial health!' :
               score >= 60 ? 'Good, with room for improvement' :
               'Needs attention'}
            </p>
          </div>

          <Separator />

          {/* Component Scores */}
          <div>
            <h4 className="font-medium text-sm mb-3">Score Breakdown</h4>
            <div className="space-y-3">
              {componentList.map((comp) => (
                <div key={comp.name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      {componentLabels[comp.name]?.icon}
                      <span>{comp.label}</span>
                    </div>
                    <span className={cn('font-medium text-sm', getScoreColor(comp.score))}>
                      {comp.score}/100
                    </span>
                  </div>
                  <Progress
                    value={comp.score}
                    className={cn('h-2', getProgressColor(comp.score))}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Strengths */}
          {strengths.length > 0 && (
            <>
              <Separator />
              <div>
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" /> Strengths
                </h4>
                <ul className="space-y-1">
                  {strengths.map((s, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-green-500 mt-1">+</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* Areas to Improve */}
          {improvements.length > 0 && (
            <>
              <Separator />
              <div>
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2 text-orange-600">
                  <AlertTriangle className="h-4 w-4" /> Areas to Improve
                </h4>
                <ul className="space-y-1">
                  {improvements.map((s, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="text-orange-500 mt-1">!</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <>
              <Separator />
              <div>
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2 text-blue-600">
                  <Lightbulb className="h-4 w-4" /> Recommendations
                </h4>
                <ul className="space-y-2">
                  {recommendations.slice(0, 4).map((r, i) => (
                    <li
                      key={i}
                      className="text-sm p-2 bg-accent/50 rounded cursor-pointer hover:bg-accent flex items-center justify-between"
                      onClick={() => {
                        // Could navigate to relevant page based on recommendation
                        onClose()
                        router.push('/budget')
                      }}
                    >
                      <span>{r}</span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>

        <DialogFooter className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={() => {
            onClose()
            router.push('/budget')
          }}>
            Improve Score <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
