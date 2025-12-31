'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Lightbulb,
  ChevronRight,
  Check,
  X,
  Clock,
  Loader2,
  Home,
  Car,
  TrendingUp,
  Coins,
} from 'lucide-react'
import {
  useNetWorthSuggestions,
  useAcceptSuggestion,
  useDismissSuggestion,
  useSnoozeSuggestion,
  NetWorthSuggestion,
  formatConfidence,
} from '@/hooks/useNetWorth'
import { toast } from '@/components/ui/Toaster'
import { cn } from '@/lib/utils'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function getSuggestionIcon(type: string) {
  switch (type) {
    case 'property':
      return <Home className="h-5 w-5 text-blue-500" />
    case 'vehicle':
      return <Car className="h-5 w-5 text-green-500" />
    case 'investment':
      return <TrendingUp className="h-5 w-5 text-purple-500" />
    case 'precious_metal':
      return <Coins className="h-5 w-5 text-yellow-500" />
    default:
      return <Lightbulb className="h-5 w-5 text-orange-500" />
  }
}

function getSuggestionLabel(type: string, subtype?: string): string {
  if (type === 'property' && subtype === 'mortgage') return 'Mortgage Detected'
  if (type === 'property') return 'Property Detected'
  if (type === 'vehicle' && subtype === 'auto_loan') return 'Auto Loan Detected'
  if (type === 'vehicle') return 'Vehicle Detected'
  if (type === 'investment') return 'Investment Detected'
  if (type === 'precious_metal') return 'Metal Purchase Detected'
  return 'Asset Detected'
}

export function SuggestionsCard() {
  const router = useRouter()
  const { data, isLoading } = useNetWorthSuggestions()
  const acceptSuggestion = useAcceptSuggestion()
  const dismissSuggestion = useDismissSuggestion()
  const snoozeSuggestion = useSnoozeSuggestion()

  const [selectedSuggestion, setSelectedSuggestion] = useState<NetWorthSuggestion | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const suggestions = data?.suggestions || []
  const pendingCount = suggestions.length

  const handleAccept = async (suggestion: NetWorthSuggestion) => {
    setActionLoading(suggestion.id)
    try {
      await acceptSuggestion.mutateAsync({ suggestionId: suggestion.id })
      toast.success('Asset/liability added to your net worth')
      setSelectedSuggestion(null)
    } catch {
      toast.error('Failed to accept suggestion')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDismiss = async (suggestion: NetWorthSuggestion) => {
    setActionLoading(suggestion.id)
    try {
      await dismissSuggestion.mutateAsync(suggestion.id)
      toast.success('Suggestion dismissed')
      setSelectedSuggestion(null)
    } catch {
      toast.error('Failed to dismiss')
    } finally {
      setActionLoading(null)
    }
  }

  const handleSnooze = async (suggestion: NetWorthSuggestion) => {
    setActionLoading(suggestion.id)
    try {
      await snoozeSuggestion.mutateAsync({ suggestionId: suggestion.id, days: 7 })
      toast.success('Snoozed for 7 days')
      setSelectedSuggestion(null)
    } catch {
      toast.error('Failed to snooze')
    } finally {
      setActionLoading(null)
    }
  }

  // Don't show card if no suggestions
  if (!isLoading && pendingCount === 0) {
    return null
  }

  return (
    <>
      <Card className="border-orange-200 dark:border-orange-900/50 bg-orange-50/50 dark:bg-orange-950/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-orange-500" />
              Smart Suggestions
              {pendingCount > 0 && (
                <Badge variant="secondary" className="bg-orange-100 text-orange-700">
                  {pendingCount} new
                </Badge>
              )}
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/networth')}
            >
              View All <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-2">
              {suggestions.slice(0, 3).map((suggestion) => (
                <div
                  key={suggestion.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-background cursor-pointer hover:bg-accent/50 transition-colors"
                  onClick={() => setSelectedSuggestion(suggestion)}
                >
                  <div className="flex items-center gap-3">
                    {getSuggestionIcon(suggestion.type)}
                    <div>
                      <div className="font-medium text-sm">
                        {getSuggestionLabel(suggestion.type, suggestion.subtype)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {suggestion.source_data?.lender || suggestion.source_data?.merchant || 'From recurring payments'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-sm">
                      {formatCurrency(
                        suggestion.suggested_values?.monthly_payment ||
                        suggestion.suggested_values?.purchase_amount ||
                        suggestion.suggested_values?.contribution_amount ||
                        0
                      )}
                      {suggestion.suggested_values?.monthly_payment && (
                        <span className="text-muted-foreground text-xs">/mo</span>
                      )}
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {formatConfidence(suggestion.confidence)}
                    </Badge>
                  </div>
                </div>
              ))}

              {pendingCount > 3 && (
                <Button
                  variant="ghost"
                  className="w-full text-sm"
                  onClick={() => router.push('/networth')}
                >
                  +{pendingCount - 3} more suggestions
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Suggestion Detail Modal */}
      <Dialog open={!!selectedSuggestion} onOpenChange={() => setSelectedSuggestion(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedSuggestion && getSuggestionIcon(selectedSuggestion.type)}
              {selectedSuggestion && getSuggestionLabel(selectedSuggestion.type, selectedSuggestion.subtype)}
            </DialogTitle>
          </DialogHeader>

          {selectedSuggestion && (
            <div className="space-y-4">
              {/* Source info */}
              <div className="p-3 bg-muted rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">Detected from</div>
                <div className="font-medium">
                  {selectedSuggestion.source_data?.lender ||
                    selectedSuggestion.source_data?.merchant ||
                    selectedSuggestion.recurring_name ||
                    'Recurring payment'}
                </div>
                {selectedSuggestion.source_data?.monthly_payment && (
                  <div className="text-sm text-muted-foreground">
                    {formatCurrency(selectedSuggestion.source_data.monthly_payment)}/month payment
                  </div>
                )}
              </div>

              {/* Suggested values */}
              <div>
                <div className="text-sm font-medium mb-2">Suggested Details</div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {selectedSuggestion.suggested_values?.original_amount && (
                    <>
                      <div className="text-muted-foreground">Original Amount</div>
                      <div className="font-medium">
                        {formatCurrency(selectedSuggestion.suggested_values.original_amount)}
                      </div>
                    </>
                  )}
                  {selectedSuggestion.suggested_values?.current_balance && (
                    <>
                      <div className="text-muted-foreground">Est. Balance</div>
                      <div className="font-medium">
                        {formatCurrency(selectedSuggestion.suggested_values.current_balance)}
                      </div>
                    </>
                  )}
                  {selectedSuggestion.suggested_values?.interest_rate && (
                    <>
                      <div className="text-muted-foreground">Est. Rate</div>
                      <div className="font-medium">
                        {(selectedSuggestion.suggested_values.interest_rate * 100).toFixed(1)}%
                      </div>
                    </>
                  )}
                  {selectedSuggestion.suggested_values?.term_months && (
                    <>
                      <div className="text-muted-foreground">Term</div>
                      <div className="font-medium">
                        {Math.round(selectedSuggestion.suggested_values.term_months / 12)} years
                      </div>
                    </>
                  )}
                  {selectedSuggestion.suggested_values?.total_contributed && (
                    <>
                      <div className="text-muted-foreground">Total Contributed</div>
                      <div className="font-medium">
                        {formatCurrency(selectedSuggestion.suggested_values.total_contributed)}
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Confidence */}
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Confidence</span>
                <Badge
                  variant="outline"
                  className={cn(
                    selectedSuggestion.confidence >= 0.75 && 'border-green-500 text-green-600',
                    selectedSuggestion.confidence >= 0.5 && selectedSuggestion.confidence < 0.75 && 'border-yellow-500 text-yellow-600',
                    selectedSuggestion.confidence < 0.5 && 'border-red-500 text-red-600'
                  )}
                >
                  {formatConfidence(selectedSuggestion.confidence)} ({Math.round(selectedSuggestion.confidence * 100)}%)
                </Badge>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button
                  className="flex-1"
                  onClick={() => handleAccept(selectedSuggestion)}
                  disabled={actionLoading === selectedSuggestion.id}
                >
                  {actionLoading === selectedSuggestion.id ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Check className="h-4 w-4 mr-2" />
                  )}
                  Add to Net Worth
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleSnooze(selectedSuggestion)}
                  disabled={actionLoading === selectedSuggestion.id}
                >
                  <Clock className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => handleDismiss(selectedSuggestion)}
                  disabled={actionLoading === selectedSuggestion.id}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
