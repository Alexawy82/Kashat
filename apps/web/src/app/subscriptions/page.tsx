"use client"

import { useEffect, useMemo, useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Check,
  CheckCircle2,
  Clock,
  Loader2,
  RefreshCw,
  Repeat,
  Sparkles,
  X,
  XCircle,
} from 'lucide-react'
import {
  useConfirmedRecurring,
  useRecurringSuggestions,
  useRunRecurringDetection,
} from '@/hooks/useAutomation'
import {
  useBills,
  useCancellationRisks,
  useConfirmWithLearning,
  useCreditCards,
  useInsurance,
  useLoans,
  useOptimizations,
  useRecurringInsights,
  useRecurringSummary,
  useRejectWithLearning,
  useSubscriptions,
  useUpcomingPayments,
  useSpendingByType,
} from '@/hooks/useRecurring'
import { SummaryBar } from '@/app/subscriptions/components/SummaryBar'
import { AlertsBanner } from '@/app/subscriptions/components/AlertsBanner'
import { InsightsPanel } from '@/app/subscriptions/components/InsightsPanel'
import { UpcomingWidget } from '@/app/subscriptions/components/UpcomingWidget'
import { SeriesDetailSheet } from '@/app/subscriptions/components/SeriesDetailSheet'
import { ReportsModal } from '@/app/subscriptions/components/ReportsModal'
import { TypeTabs, TypeTab } from '@/app/subscriptions/components/TypeTabs'
import { CategoryOverview } from '@/app/subscriptions/components/CategoryOverview'
import { formatAmount, getCadenceLabel, getMerchantName } from '@/app/subscriptions/lib/recurringUtils'

function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const color = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-orange-500'

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-muted rounded-full h-1.5 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-8">{pct}%</span>
    </div>
  )
}

export default function SubscriptionsPage() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [includeShortCadence, setIncludeShortCadence] = useState(false)
  const [actionResult, setActionResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [selectedSeries, setSelectedSeries] = useState<any | null>(null)
  const [reportsOpen, setReportsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('all')

  const { data: suggestionsData, isLoading: suggestionsLoading } = useRecurringSuggestions()
  const { data: confirmed, isLoading: confirmedLoading } = useConfirmedRecurring()
  const { data: summary, isLoading: summaryLoading } = useRecurringSummary()
  const { data: subscriptions, isLoading: subscriptionsLoading } = useSubscriptions()
  const { data: bills, isLoading: billsLoading } = useBills()
  const { data: loans, isLoading: loansLoading } = useLoans()
  const { data: creditCards, isLoading: creditCardsLoading } = useCreditCards()
  const { data: insurance, isLoading: insuranceLoading } = useInsurance()
  const { data: insights, isLoading: insightsLoading } = useRecurringInsights()
  const { data: optimizations, isLoading: optimizationsLoading } = useOptimizations()
  const { data: cancellationRisks, isLoading: risksLoading } = useCancellationRisks()
  const { data: upcomingPayments, isLoading: upcomingLoading } = useUpcomingPayments(14)
  const { data: spendingByType } = useSpendingByType()

  const confirmRecurring = useConfirmWithLearning()
  const rejectRecurring = useRejectWithLearning()
  const runDetection = useRunRecurringDetection()

  const candidates = useMemo(() => (suggestionsData as any[]) || [], [suggestionsData])
  const confirmedList = useMemo(() => (confirmed as any[]) || [], [confirmed])

  const overdueSeries = useMemo(
    () => confirmedList.filter((x: any) => x.status === 'overdue'),
    [confirmedList]
  )
  const priceHikeSeries = useMemo(
    () => confirmedList.filter((x: any) => x.price_hike),
    [confirmedList]
  )
  const upcomingThisWeek = useMemo(() => {
    const items = (upcomingPayments as any[]) || []
    const today = new Date()
    const weekAhead = new Date(today)
    weekAhead.setDate(today.getDate() + 7)
    return items.filter((item) => {
      if (!item.date) return false
      const date = new Date(item.date)
      return date >= today && date <= weekAhead
    })
  }, [upcomingPayments])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const stored = window.localStorage.getItem('recurring-active-tab')
    if (stored) setActiveTab(stored)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('recurring-active-tab', activeTab)
  }, [activeTab])

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(candidates.map((c: any) => c.id || c.series_id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleSelect = (id: string, checked: boolean) => {
    const next = new Set(selectedIds)
    if (checked) next.add(id)
    else next.delete(id)
    setSelectedIds(next)
  }

  const handleBulkConfirm = () => {
    const ids = Array.from(selectedIds)
    confirmRecurring.mutate(ids, {
      onSuccess: () => {
        setSelectedIds(new Set())
        setActionResult({ type: 'success', message: `Confirmed ${ids.length} recurring patterns` })
        setTimeout(() => setActionResult(null), 3000)
      },
    })
  }

  const handleBulkReject = () => {
    const ids = Array.from(selectedIds)
    rejectRecurring.mutate({ seriesIds: ids }, {
      onSuccess: () => {
        setSelectedIds(new Set())
        setActionResult({ type: 'success', message: `Rejected ${ids.length} patterns` })
        setTimeout(() => setActionResult(null), 3000)
      },
    })
  }

  const handleConfirm = (id: string) => {
    confirmRecurring.mutate([id])
  }

  const handleReject = (id: string) => {
    rejectRecurring.mutate({ seriesIds: [id] })
  }

  const handleRunDetection = () => {
    runDetection.mutate({ min_occurrences: 2, include_short_cadence: includeShortCadence })
  }

  const typeTabs: TypeTab[] = [
    {
      key: 'all',
      label: 'All',
      title: 'All Recurring',
      description: 'Everything currently confirmed across all categories.',
      items: confirmedList,
      isLoading: confirmedLoading,
      onSelect: setSelectedSeries,
    },
    {
      key: 'subscriptions',
      label: 'Subscriptions',
      title: 'Subscriptions',
      description: 'Streaming, software, memberships, and other services.',
      items: (subscriptions as any[]) || [],
      isLoading: subscriptionsLoading,
      onSelect: setSelectedSeries,
    },
    {
      key: 'bills',
      label: 'Housing & Utilities',
      title: 'Housing & Utilities',
      description: 'Rent, mortgage, utilities, and household essentials.',
      items: (bills as any[]) || [],
      isLoading: billsLoading,
      onSelect: setSelectedSeries,
    },
    {
      key: 'loans',
      label: 'Loans',
      title: 'Loans & Debt',
      description: 'Mortgages, auto loans, student loans, and BNPL.',
      items: (loans as any[]) || [],
      isLoading: loansLoading,
      onSelect: setSelectedSeries,
    },
    {
      key: 'credit-cards',
      label: 'Credit Cards',
      title: 'Credit Cards',
      description: 'Recurring card payments and statements.',
      items: (creditCards as any[]) || [],
      isLoading: creditCardsLoading,
      onSelect: setSelectedSeries,
    },
    {
      key: 'insurance',
      label: 'Insurance',
      title: 'Insurance',
      description: 'Auto, home, health, life, and pet insurance.',
      items: (insurance as any[]) || [],
      isLoading: insuranceLoading,
      onSelect: setSelectedSeries,
    },
  ]

  const tabKeys = useMemo(() => typeTabs.map((tab) => tab.key), [typeTabs])

  useEffect(() => {
    if (tabKeys.length === 0) return
    if (!tabKeys.includes(activeTab)) {
      setActiveTab(tabKeys[0])
    }
  }, [activeTab, tabKeys])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Subscriptions</h1>
          <p className="text-muted-foreground mt-1">
            Track, manage, and optimize all your recurring charges
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => setReportsOpen(true)}>
            Reports
          </Button>
          <div className="flex items-center gap-2">
            <Switch id="short-cadence" checked={includeShortCadence} onCheckedChange={setIncludeShortCadence} />
            <Label htmlFor="short-cadence" className="text-sm text-muted-foreground">
              Include weekly
            </Label>
          </div>
          <Button
            variant="outline"
            onClick={handleRunDetection}
            disabled={runDetection.isPending}
            className="gap-2"
          >
            {runDetection.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Detect Patterns
          </Button>
        </div>
      </div>

      {actionResult && (
        <Alert className={actionResult.type === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}>
          {actionResult.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <XCircle className="h-4 w-4 text-red-600" />
          )}
          <AlertDescription className={actionResult.type === 'success' ? 'text-green-700' : 'text-red-700'}>
            {actionResult.message}
          </AlertDescription>
        </Alert>
      )}

      <SummaryBar summary={summary as any} pendingCount={candidates.length} isLoading={summaryLoading} />

      <AlertsBanner
        overdueItems={overdueSeries}
        dueSoonItems={upcomingThisWeek}
        priceHikeItems={priceHikeSeries}
        onItemClick={(item) => setSelectedSeries(item)}
      />

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <InsightsPanel
          insights={(insights as any[]) || []}
          optimizations={(optimizations as any[]) || []}
          risks={(cancellationRisks as any[]) || []}
          isLoading={insightsLoading || optimizationsLoading || risksLoading}
          onSeriesClick={(seriesId) => {
            // Find series in confirmedList
            const series = confirmedList.find((s: any) =>
              s.id === seriesId || s.series_id === seriesId
            )
            if (series) {
              setSelectedSeries(series)
            }
          }}
        />
        <UpcomingWidget
          items={(upcomingPayments as any[]) || []}
          isLoading={upcomingLoading}
          onItemClick={(item) => {
            // Find full series in confirmedList
            const series = confirmedList.find((s: any) =>
              s.id === item.series_id || s.series_id === item.series_id
            )
            if (series) {
              setSelectedSeries(series)
            }
          }}
        />
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Pending Review
              </CardTitle>
              <CardDescription>Review and confirm detected recurring payment patterns.</CardDescription>
            </div>
            {selectedIds.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkReject}
                  disabled={rejectRecurring.isPending}
                  className="gap-1"
                >
                  <X className="h-3.5 w-3.5" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  onClick={handleBulkConfirm}
                  disabled={confirmRecurring.isPending}
                  className="gap-1"
                >
                  <Check className="h-3.5 w-3.5" />
                  Confirm All
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {suggestionsLoading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : candidates.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Repeat className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="font-medium">No patterns detected</p>
              <p className="text-sm mt-1">Click "Detect Patterns" to scan for recurring payments</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={selectedIds.size === candidates.length && candidates.length > 0}
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead>Merchant</TableHead>
                  <TableHead>Cadence</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Next Due</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {candidates.map((item: any) => {
                  const id = item.id || item.series_id
                  return (
                    <TableRow key={id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedIds.has(id)}
                          onCheckedChange={(checked) => handleSelect(id, !!checked)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">{getMerchantName(item)}</div>
                        {item.occurrences && (
                          <div className="text-xs text-muted-foreground">{item.occurrences} occurrences</div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{getCadenceLabel(item)}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatAmount(item.amount_mean || item.amount || 0)}
                        {item.is_variable && <span className="text-xs text-muted-foreground ml-1">~</span>}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.next_date || '—'}</TableCell>
                      <TableCell>
                        <ConfidenceIndicator confidence={item.confidence || 0.5} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8"
                            onClick={() => handleReject(id)}
                            disabled={rejectRecurring.isPending}
                          >
                            <X className="h-4 w-4 text-muted-foreground hover:text-red-500" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8"
                            onClick={() => handleConfirm(id)}
                            disabled={confirmRecurring.isPending}
                          >
                            <Check className="h-4 w-4 text-muted-foreground hover:text-green-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Spending Breakdown</h2>
            <p className="text-sm text-muted-foreground">
              Your recurring charges organized by category. Click a category to explore.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Updated moments ago</span>
          </div>
        </div>

        <CategoryOverview
          data={spendingByType as any}
          isLoading={false}
          onCategoryClick={(categoryType) => {
            // Map API category types to tab keys
            const categoryToTab: Record<string, string> = {
              subscriptions: 'subscriptions',
              rent_and_utilities: 'bills',
              loan_payments: 'loans',
              credit_card: 'credit-cards',
              insurance: 'insurance',
              unknown: 'all',
            }
            const tabKey = categoryToTab[categoryType] || 'all'
            setActiveTab(tabKey)
          }}
        />

        <div className="pt-4">
          <h3 className="text-lg font-semibold mb-3">Detailed View</h3>
          <TypeTabs tabs={typeTabs} value={activeTab} onValueChange={setActiveTab} />
        </div>
      </div>

      <SeriesDetailSheet
        open={Boolean(selectedSeries)}
        onOpenChange={(next) => {
          if (!next) setSelectedSeries(null)
        }}
        series={selectedSeries}
      />

      <ReportsModal
        open={reportsOpen}
        onOpenChange={setReportsOpen}
        summary={summary as any}
        spending={spendingByType as any}
      />
    </div>
  )
}
