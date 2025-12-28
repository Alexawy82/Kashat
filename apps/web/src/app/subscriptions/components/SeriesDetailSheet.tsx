"use client"

import { useEffect, useMemo, useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Calendar, CreditCard, PauseCircle, RotateCcw, XCircle } from 'lucide-react'
import { useRecurringSparkline } from '@/hooks/useAutomation'
import { formatAmount, getCadenceLabel, getMerchantName, RecurringSeries } from '@/app/subscriptions/lib/recurringUtils'
import { useSubmitFeedback } from '@/hooks/useRecurring'

function Sparkline({ data, width = 220, height = 60 }: { data: number[]; width?: number; height?: number }) {
  if (!data || data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width
      const y = height - ((v - min) / range) * (height - 8) - 4
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" className="text-primary" />
    </svg>
  )
}

export function SeriesDetailSheet({
  open,
  onOpenChange,
  series,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  series: RecurringSeries | null
}) {
  const seriesId = series?.id || series?.series_id || null
  const { data: transactions, isLoading } = useRecurringSparkline(seriesId)
  const sparklineData = useMemo(() => (transactions || []).map((t: any) => Math.abs(t.amount || 0)), [transactions])
  const history = useMemo(() => (transactions || []).slice(0, 6), [transactions])
  const typeOptions = ['subscription', 'bill', 'loan', 'credit_card', 'insurance', 'other'] as const
  const categoryOptions = ['unknown', 'streaming', 'utilities', 'mortgage', 'insurance'] as const
  const typeValue = typeOptions.includes(series?.recurring_type) ? series?.recurring_type : 'subscription'
  const categoryValue = categoryOptions.includes(series?.category_name) ? series?.category_name : 'unknown'
  const [selectedType, setSelectedType] = useState(typeValue)
  const [selectedCategory, setSelectedCategory] = useState(categoryValue)
  const [isEssential, setIsEssential] = useState(Boolean(series?.is_essential))
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null)
  const submitFeedback = useSubmitFeedback()

  useEffect(() => {
    setSelectedType(typeValue)
    setSelectedCategory(categoryValue)
    setIsEssential(Boolean(series?.is_essential))
    setFeedbackStatus(null)
  }, [series?.id, series?.series_id, typeValue, categoryValue, series?.is_essential])

  const handleSaveFeedback = () => {
    if (!seriesId || !series) return
    const originalType = series.recurring_type || 'unknown'
    const originalEssential = Boolean(series.is_essential)
    const correctedType = selectedType !== originalType ? selectedType : null
    const correctedEssential = isEssential !== originalEssential ? isEssential : null
    const wasCorrect = !correctedType && correctedEssential === null

    submitFeedback.mutate(
      {
        series_id: seriesId,
        original_type: originalType,
        corrected_type: correctedType,
        was_correct: wasCorrect,
        merchant_pattern: getMerchantName(series),
        is_essential: originalEssential,
        corrected_is_essential: correctedEssential,
      },
      {
        onSuccess: () => {
          setFeedbackStatus('Saved. Thanks for improving the model.')
        },
        onError: () => {
          setFeedbackStatus('Unable to save feedback. Try again.')
        },
      }
    )
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{series ? getMerchantName(series) : 'Recurring Detail'}</SheetTitle>
        </SheetHeader>

        {!series ? (
          <div className="text-sm text-muted-foreground mt-6">Select a recurring series to view details.</div>
        ) : (
          <div className="mt-6 space-y-6">
            <div className="grid gap-3 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">Amount</div>
                <div className="text-lg font-semibold">{formatAmount(series.amount_mean || series.amount || 0)}</div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">Cadence</div>
                <Badge variant="outline">{getCadenceLabel(series)}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">Next Due</div>
                <div className="text-sm font-medium">{series.next_date || '—'}</div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Payment History</h3>
                <Badge variant="secondary" className="text-[10px]">Last 12</Badge>
              </div>
              {isLoading ? (
                <div className="text-sm text-muted-foreground">Loading history…</div>
              ) : sparklineData.length > 1 ? (
                <Sparkline data={sparklineData} />
              ) : (
                <div className="text-sm text-muted-foreground">No history available.</div>
              )}
              {history.length > 0 && (
                <div className="space-y-2">
                  {history.map((row: any) => (
                    <div key={row.date} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{row.date}</span>
                      <span className="font-medium">{formatAmount(row.amount || 0)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="h-px bg-border" />

            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Actions</h3>
              <div className="grid gap-2 sm:grid-cols-2">
                <Button variant="outline" className="gap-2" disabled>
                  <CreditCard className="h-4 w-4" />
                  Mark Paid
                </Button>
                <Button variant="outline" className="gap-2" disabled>
                  <RotateCcw className="h-4 w-4" />
                  Skip Next
                </Button>
                <Button variant="outline" className="gap-2" disabled>
                  <PauseCircle className="h-4 w-4" />
                  Pause
                </Button>
                <Button variant="outline" className="gap-2" disabled>
                  <XCircle className="h-4 w-4" />
                  Cancel
                </Button>
              </div>
            </div>

            <div className="h-px bg-border" />

            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Classification</h3>
              <div className="grid gap-3">
                <div className="grid gap-2">
                  <Label>Type</Label>
                  <Select value={selectedType} onValueChange={(value) => setSelectedType(value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="subscription">Subscription</SelectItem>
                      <SelectItem value="bill">Bill</SelectItem>
                      <SelectItem value="loan">Loan</SelectItem>
                      <SelectItem value="credit_card">Credit Card</SelectItem>
                      <SelectItem value="insurance">Insurance</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label>Category</Label>
                  <Select value={selectedCategory} onValueChange={(value) => setSelectedCategory(value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unknown">Unknown</SelectItem>
                      <SelectItem value="streaming">Streaming</SelectItem>
                      <SelectItem value="utilities">Utilities</SelectItem>
                      <SelectItem value="mortgage">Mortgage</SelectItem>
                      <SelectItem value="insurance">Insurance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div className="space-y-0.5">
                    <Label>Essential</Label>
                    <p className="text-xs text-muted-foreground">Mark as must-pay</p>
                  </div>
                  <Switch checked={isEssential} onCheckedChange={setIsEssential} />
                </div>
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={handleSaveFeedback}
                  disabled={submitFeedback.isPending}
                >
                  <Calendar className="h-4 w-4" />
                  {submitFeedback.isPending ? 'Saving…' : 'Save & Train AI'}
                </Button>
                {feedbackStatus && (
                  <p className="text-xs text-muted-foreground">{feedbackStatus}</p>
                )}
              </div>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
