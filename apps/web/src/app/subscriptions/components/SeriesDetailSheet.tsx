"use client"

import { useEffect, useMemo, useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Calendar, CreditCard, PauseCircle, PlayCircle, RotateCcw, XCircle } from 'lucide-react'
import { useRecurringSparkline } from '@/hooks/useAutomation'
import { formatAmount, getCadenceLabel, getMerchantName, RecurringSeries } from '@/app/subscriptions/lib/recurringUtils'
import { useSubmitFeedback, useMarkPaid, useSkipNext, usePauseSeries, useResumeSeries, useCancelSeries } from '@/hooks/useRecurring'

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
  const history = useMemo(() => transactions || [], [transactions])
  const [showAllHistory, setShowAllHistory] = useState(false)
  const displayedHistory = showAllHistory ? history : history.slice(0, 6)

  // Calculate trend analysis
  const trendAnalysis = useMemo(() => {
    if (!transactions || transactions.length < 2) return null

    const amounts = transactions.map((t: any) => Math.abs(t.amount || 0))
    const latest = amounts[0]
    const previous = amounts[1]
    const oldest = amounts[amounts.length - 1]
    const average = amounts.reduce((a: number, b: number) => a + b, 0) / amounts.length
    const min = Math.min(...amounts)
    const max = Math.max(...amounts)

    // Calculate change from previous
    const changeFromPrevious = latest - previous
    const changePercent = previous > 0 ? ((latest - previous) / previous) * 100 : 0

    // Calculate overall trend (first vs last)
    const overallChange = latest - oldest
    const overallPercent = oldest > 0 ? ((latest - oldest) / oldest) * 100 : 0

    return {
      latest,
      previous,
      average,
      min,
      max,
      changeFromPrevious,
      changePercent,
      overallChange,
      overallPercent,
      isIncreasing: changeFromPrevious > 0,
      hasVariance: max - min > average * 0.05, // More than 5% variance
    }
  }, [transactions])
  const typeOptions = ['subscription', 'bill', 'loan', 'credit_card', 'insurance', 'other'] as const
  const categoryOptions = ['unknown', 'streaming', 'utilities', 'mortgage', 'insurance'] as const
  const typeValue = typeOptions.includes(series?.recurring_type) ? series?.recurring_type : 'subscription'
  const categoryValue = categoryOptions.includes(series?.category_name) ? series?.category_name : 'unknown'
  const [selectedType, setSelectedType] = useState(typeValue)
  const [selectedCategory, setSelectedCategory] = useState(categoryValue)
  const [isEssential, setIsEssential] = useState(Boolean(series?.is_essential))
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null)
  const [actionStatus, setActionStatus] = useState<string | null>(null)
  const submitFeedback = useSubmitFeedback()
  const markPaid = useMarkPaid()
  const skipNext = useSkipNext()
  const pauseSeries = usePauseSeries()
  const resumeSeries = useResumeSeries()
  const cancelSeries = useCancelSeries()
  const isPaused = series?.status === 'paused'
  const isActionPending = markPaid.isPending || skipNext.isPending || pauseSeries.isPending || resumeSeries.isPending || cancelSeries.isPending

  useEffect(() => {
    setSelectedType(typeValue)
    setSelectedCategory(categoryValue)
    setIsEssential(Boolean(series?.is_essential))
    setFeedbackStatus(null)
    setActionStatus(null)
  }, [series?.id, series?.series_id, typeValue, categoryValue, series?.is_essential])

  const handleMarkPaid = () => {
    if (!seriesId) return
    setActionStatus(null)
    markPaid.mutate(seriesId, {
      onSuccess: (data) => {
        setActionStatus(`Marked paid. Next due: ${data.next_due_date || 'N/A'}`)
      },
      onError: () => setActionStatus('Failed to mark as paid'),
    })
  }

  const handleSkipNext = () => {
    if (!seriesId) return
    setActionStatus(null)
    skipNext.mutate(seriesId, {
      onSuccess: (data) => {
        setActionStatus(`Skipped. Next due: ${data.new_next_date || 'N/A'}`)
      },
      onError: () => setActionStatus('Failed to skip'),
    })
  }

  const handlePauseResume = () => {
    if (!seriesId) return
    setActionStatus(null)
    if (isPaused) {
      resumeSeries.mutate(seriesId, {
        onSuccess: (data) => {
          setActionStatus(`Resumed. Next due: ${data.next_date || 'N/A'}`)
        },
        onError: () => setActionStatus('Failed to resume'),
      })
    } else {
      pauseSeries.mutate(seriesId, {
        onSuccess: () => {
          setActionStatus('Paused. Will not appear in bills until resumed.')
        },
        onError: () => setActionStatus('Failed to pause'),
      })
    }
  }

  const handleCancel = () => {
    if (!seriesId) return
    if (!confirm('Are you sure you want to cancel this recurring series? This will remove it from bills/calendar.')) return
    setActionStatus(null)
    cancelSeries.mutate(seriesId, {
      onSuccess: () => {
        setActionStatus('Cancelled. This series has been removed.')
        onOpenChange(false) // Close the sheet
      },
      onError: () => setActionStatus('Failed to cancel'),
    })
  }

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
                <div className="text-sm text-muted-foreground">Latest Payment</div>
                <div className="text-lg font-semibold">
                  {formatAmount(trendAnalysis?.latest || series.amount_mean || series.amount || 0)}
                </div>
              </div>
              {trendAnalysis && trendAnalysis.changePercent !== 0 && (
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">vs Previous</div>
                  <div className={`text-sm font-medium ${trendAnalysis.isIncreasing ? 'text-red-600' : 'text-green-600'}`}>
                    {trendAnalysis.isIncreasing ? '↑' : '↓'} {formatAmount(Math.abs(trendAnalysis.changeFromPrevious))} ({trendAnalysis.changePercent.toFixed(1)}%)
                  </div>
                </div>
              )}
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">Average</div>
                <div className="text-sm">{formatAmount(trendAnalysis?.average || series.amount_mean || 0)}</div>
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

            {/* Trend Analysis */}
            {trendAnalysis && trendAnalysis.hasVariance && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">Payment Trend</h3>
                <div className="text-sm text-amber-700">
                  {trendAnalysis.overallPercent > 5 ? (
                    <>
                      <span className="font-medium">↑ Increased {trendAnalysis.overallPercent.toFixed(1)}%</span>
                      <span> from {formatAmount(trendAnalysis.min)} to {formatAmount(trendAnalysis.max)}</span>
                    </>
                  ) : trendAnalysis.overallPercent < -5 ? (
                    <>
                      <span className="font-medium">↓ Decreased {Math.abs(trendAnalysis.overallPercent).toFixed(1)}%</span>
                      <span> from {formatAmount(trendAnalysis.max)} to {formatAmount(trendAnalysis.min)}</span>
                    </>
                  ) : (
                    <>
                      <span className="font-medium">Variable payment</span>
                      <span> ranging {formatAmount(trendAnalysis.min)} - {formatAmount(trendAnalysis.max)}</span>
                    </>
                  )}
                </div>
              </div>
            )}

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
                  {displayedHistory.map((row: any) => (
                    <div key={row.date} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{row.date}</span>
                      <span className="font-medium">{formatAmount(row.amount || 0)}</span>
                    </div>
                  ))}
                  {history.length > 6 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full text-xs"
                      onClick={() => setShowAllHistory(!showAllHistory)}
                    >
                      {showAllHistory ? 'Show Less' : `Show All ${history.length} Payments`}
                    </Button>
                  )}
                </div>
              )}
            </div>

            <div className="h-px bg-border" />

            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Actions</h3>
              <div className="grid gap-2 sm:grid-cols-2">
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={handleMarkPaid}
                  disabled={isActionPending}
                >
                  <CreditCard className="h-4 w-4" />
                  {markPaid.isPending ? 'Marking...' : 'Mark Paid'}
                </Button>
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={handleSkipNext}
                  disabled={isActionPending}
                >
                  <RotateCcw className="h-4 w-4" />
                  {skipNext.isPending ? 'Skipping...' : 'Skip Next'}
                </Button>
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={handlePauseResume}
                  disabled={isActionPending}
                >
                  {isPaused ? (
                    <>
                      <PlayCircle className="h-4 w-4" />
                      {resumeSeries.isPending ? 'Resuming...' : 'Resume'}
                    </>
                  ) : (
                    <>
                      <PauseCircle className="h-4 w-4" />
                      {pauseSeries.isPending ? 'Pausing...' : 'Pause'}
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                  onClick={handleCancel}
                  disabled={isActionPending}
                >
                  <XCircle className="h-4 w-4" />
                  {cancelSeries.isPending ? 'Cancelling...' : 'Cancel'}
                </Button>
              </div>
              {actionStatus && (
                <p className="text-xs text-muted-foreground">{actionStatus}</p>
              )}
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
