"use client"

import { useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Progress } from "@/components/ui/progress"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  ArrowRight,
  Check,
  X,
  Loader2,
  ArrowRightLeft,
  CheckCircle,
  ArrowUpDown,
  Zap,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Building2,
  Wallet,
  Brain,
  Sparkles,
} from "lucide-react"
import {
  useTransferSuggestions,
  useConfirmedTransfers,
  useConfirmTransfer,
  useRejectTransfer,
  useBulkConfirmTransfers,
  useBulkRejectTransfers,
  useRunTransferDetection,
  useRunAITransferDetection,
  useAITransferJob,
} from "@/hooks/useAutomation"

type SortOption = "confidence-desc" | "confidence-asc" | "amount-desc" | "amount-asc" | "date-desc" | "date-asc"

function formatAmount(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(Math.abs(amount))
}

function ConfidenceBadge({ confidence, method }: { confidence: number; method?: string }) {
  const pct = Math.round(confidence * 100)
  const isAI = method?.includes('ai')
  const variant = pct >= 90 ? "default" : pct >= 70 ? "secondary" : "outline"

  return (
    <div className="flex flex-col items-center gap-1">
      <Badge variant={variant} className={`text-xs ${isAI ? 'bg-purple-600' : ''}`}>
        {pct}% match
      </Badge>
      {method && (
        <div className="flex items-center gap-1">
          {isAI && <Brain className="h-3 w-3 text-purple-500" />}
          <span className={`text-[10px] capitalize ${isAI ? 'text-purple-600' : 'text-muted-foreground'}`}>
            {method.replace("hybrid-", "").replace("ai-enhanced-", "AI ").replace("-", " ")}
          </span>
        </div>
      )}
    </div>
  )
}

function TransferCard({
  match,
  isSelected,
  onSelect,
  onConfirm,
  onReject,
  isConfirming,
  isRejecting,
}: {
  match: any
  isSelected: boolean
  onSelect: (checked: boolean) => void
  onConfirm: () => void
  onReject: () => void
  isConfirming: boolean
  isRejecting: boolean
}) {
  const leftAmount = Math.abs(match.left?.amount || 0)
  const rightAmount = Math.abs(match.right?.amount || 0)
  const amountDiff = Math.abs(leftAmount - rightAmount)
  const hasAmountDiff = amountDiff > 0.01

  return (
    <Card className={`transition-all ${isSelected ? "ring-2 ring-primary" : "hover:shadow-md"}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className="pt-1">
            <Checkbox checked={isSelected} onCheckedChange={onSelect} />
          </div>

          <div className="flex-1 grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-full bg-red-100">
                  <Building2 className="h-3.5 w-3.5 text-red-600" />
                </div>
                <Badge variant="outline" className="text-[10px]">
                  {match.left?.account_id?.slice(-8) || "Account"}
                </Badge>
              </div>
              <div className="font-medium text-sm truncate max-w-[200px]">
                {match.left?.description_norm || "Unknown"}
              </div>
              <div className="text-lg font-bold text-red-600">
                -{formatAmount(leftAmount)}
              </div>
              <div className="text-xs text-muted-foreground">
                {match.left?.posted_at || match.left?.date}
              </div>
            </div>

            <div className="flex flex-col items-center justify-center px-4">
              <div className="p-2.5 bg-slate-100 rounded-full mb-2">
                <ArrowRight className="h-5 w-5 text-slate-600" />
              </div>
              <ConfidenceBadge
                confidence={match.confidence || 0.8}
                method={match.method}
              />
              {hasAmountDiff && (
                <div className="mt-1 text-[10px] text-amber-600 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {formatAmount(amountDiff)} diff
                </div>
              )}
            </div>

            <div className="space-y-1 text-right">
              <div className="flex items-center justify-end gap-2">
                <Badge variant="outline" className="text-[10px]">
                  {match.right?.account_id?.slice(-8) || "Account"}
                </Badge>
                <div className="p-1.5 rounded-full bg-green-100">
                  <Wallet className="h-3.5 w-3.5 text-green-600" />
                </div>
              </div>
              <div className="font-medium text-sm truncate max-w-[200px] ml-auto">
                {match.right?.description_norm || "Unknown"}
              </div>
              <div className="text-lg font-bold text-green-600">
                +{formatAmount(rightAmount)}
              </div>
              <div className="text-xs text-muted-foreground">
                {match.right?.posted_at || match.right?.date}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2 pl-4 border-l">
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={isConfirming}
              className="gap-1.5"
            >
              {isConfirming ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Check className="h-3.5 w-3.5" />
              )}
              Confirm
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onReject}
              disabled={isRejecting}
              className="gap-1.5"
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function TransfersTab() {
  const { data: suggestionsData, isLoading: suggestionsLoading } = useTransferSuggestions(100)
  const { data: confirmed, isLoading: confirmedLoading } = useConfirmedTransfers()

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortBy, setSortBy] = useState<SortOption>("confidence-desc")
  const [showConfirmed, setShowConfirmed] = useState(false)
  const [detectionResult, setDetectionResult] = useState<{
    created: number
    skipped_existing: number
    skipped_low_score: number
    candidates_scanned: number
  } | null>(null)
  const [aiJobId, setAIJobId] = useState<string | null>(null)

  const confirmTransfer = useConfirmTransfer()
  const rejectTransfer = useRejectTransfer()
  const bulkConfirm = useBulkConfirmTransfers()
  const bulkReject = useBulkRejectTransfers()
  const runTransfers = useRunTransferDetection()
  const runAITransfers = useRunAITransferDetection()
  const { data: aiJob } = useAITransferJob(aiJobId)

  const suggestions = suggestionsData?.suggestions || []

  const sortedSuggestions = useMemo(() => {
    const sorted = [...suggestions]
    sorted.sort((a, b) => {
      switch (sortBy) {
        case "confidence-desc":
          return (b.confidence || 0) - (a.confidence || 0)
        case "confidence-asc":
          return (a.confidence || 0) - (b.confidence || 0)
        case "amount-desc":
          return Math.abs(b.left?.amount || 0) - Math.abs(a.left?.amount || 0)
        case "amount-asc":
          return Math.abs(a.left?.amount || 0) - Math.abs(b.left?.amount || 0)
        case "date-desc":
          return (b.left?.posted_at || "").localeCompare(a.left?.posted_at || "")
        case "date-asc":
          return (a.left?.posted_at || "").localeCompare(b.left?.posted_at || "")
        default:
          return 0
      }
    })
    return sorted
  }, [suggestions, sortBy])

  const stats = useMemo(() => {
    const highConfidence = suggestions.filter((s: any) => (s.confidence || 0) >= 0.9).length
    const mediumConfidence = suggestions.filter(
      (s: any) => (s.confidence || 0) >= 0.7 && (s.confidence || 0) < 0.9
    ).length
    const lowConfidence = suggestions.filter((s: any) => (s.confidence || 0) < 0.7).length
    const totalAmount = suggestions.reduce(
      (sum: number, s: any) => sum + Math.abs(s.left?.amount || 0),
      0
    )
    return { highConfidence, mediumConfidence, lowConfidence, totalAmount }
  }, [suggestions])

  const handleConfirm = (leftId: string, rightId: string) => {
    confirmTransfer.mutate({ left_id: leftId, right_id: rightId })
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.delete(`${leftId}:${rightId}`)
      return next
    })
  }

  const handleReject = (leftId: string, rightId: string) => {
    rejectTransfer.mutate({ left_id: leftId, right_id: rightId })
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.delete(`${leftId}:${rightId}`)
      return next
    })
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const allIds = new Set(
        sortedSuggestions.map((s: any) => `${s.left_id || s.left?.id}:${s.right_id || s.right?.id}`)
      )
      setSelectedIds(allIds)
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleBulkConfirm = () => {
    const groupIds = sortedSuggestions
      .filter((s: any) => selectedIds.has(`${s.left_id || s.left?.id}:${s.right_id || s.right?.id}`))
      .map((s: any) => s.group_id)
      .filter(Boolean)
    if (groupIds.length > 0) {
      bulkConfirm.mutate(groupIds, {
        onSuccess: () => setSelectedIds(new Set()),
      })
    }
  }

  const handleBulkReject = () => {
    const groupIds = sortedSuggestions
      .filter((s: any) => selectedIds.has(`${s.left_id || s.left?.id}:${s.right_id || s.right?.id}`))
      .map((s: any) => s.group_id)
      .filter(Boolean)
    if (groupIds.length > 0) {
      bulkReject.mutate(groupIds, {
        onSuccess: () => setSelectedIds(new Set()),
      })
    }
  }

  const handleRunDetection = () => {
    runTransfers.mutate(
      { max_days: 3, amount_tolerance_pct: 0.02, min_score: 0.5 },
      {
        onSuccess: (data) => {
          setDetectionResult(data)
          setTimeout(() => setDetectionResult(null), 10000)
        },
      }
    )
  }

  const handleRunAIDetection = () => {
    runAITransfers.mutate(
      { limit: 5000, use_ai: true },
      {
        onSuccess: (data) => {
          if (data.job_id) {
            setAIJobId(data.job_id)
          }
        },
      }
    )
  }

  return (
    <div className="space-y-6">
      {/* Detection Buttons */}
      <div className="flex gap-2">
        <Button
          onClick={handleRunDetection}
          disabled={runTransfers.isPending}
          variant="outline"
          className="gap-2"
        >
          {runTransfers.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          Heuristic Scan
        </Button>
        <Button
          onClick={handleRunAIDetection}
          disabled={runAITransfers.isPending || (aiJob?.status === 'processing')}
          variant="outline"
          className="gap-2"
        >
          {runAITransfers.isPending || aiJob?.status === 'processing' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Brain className="h-4 w-4" />
          )}
          AI Detection
          <Sparkles className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* AI Job Progress */}
      {aiJob && aiJob.status === 'processing' && (
        <Card className="border-purple-200 bg-purple-50">
          <CardContent className="py-3 px-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Brain className="h-5 w-5 text-purple-600 animate-pulse" />
                  <div>
                    <p className="font-medium text-purple-800">AI Analysis in Progress</p>
                    <p className="text-sm text-purple-700">
                      Analyzing {aiJob.processed_pairs} of {aiJob.total_pairs} pairs
                    </p>
                  </div>
                </div>
                <Badge variant="outline" className="text-purple-700 border-purple-300">
                  {aiJob.progress_percent}%
                </Badge>
              </div>
              <Progress value={aiJob.progress_percent} className="h-2 bg-purple-100" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detection Result */}
      {detectionResult && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="py-3 px-4">
            <div className="flex items-center gap-4">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="font-medium text-green-800">Detection Complete</p>
                <p className="text-sm text-green-700">
                  Found {detectionResult.created} new matches
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
            <ArrowRightLeft className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{suggestions.length}</div>
            <p className="text-xs text-muted-foreground">
              {formatAmount(stats.totalAmount)} total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High Confidence</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.highConfidence}</div>
            <p className="text-xs text-muted-foreground">90%+ match score</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Confirmed</CardTitle>
            <Check className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{confirmed?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Verified transfers</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            {suggestions.length === 0 ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <AlertCircle className="h-4 w-4 text-amber-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {suggestions.length === 0 ? "Clean" : "Review"}
            </div>
            <p className="text-xs text-muted-foreground">
              {suggestions.length === 0 ? "All matched" : `${suggestions.length} pending`}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Confidence Distribution */}
      {suggestions.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Confidence Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-green-600">High (90%+)</span>
                  <span>{stats.highConfidence}</span>
                </div>
                <Progress
                  value={(stats.highConfidence / suggestions.length) * 100}
                  className="h-2 bg-green-100"
                />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-yellow-600">Medium (70-90%)</span>
                  <span>{stats.mediumConfidence}</span>
                </div>
                <Progress
                  value={(stats.mediumConfidence / suggestions.length) * 100}
                  className="h-2 bg-yellow-100"
                />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-orange-600">Low (&lt;70%)</span>
                  <span>{stats.lowConfidence}</span>
                </div>
                <Progress
                  value={(stats.lowConfidence / suggestions.length) * 100}
                  className="h-2 bg-orange-100"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Suggested Matches */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">Suggested Matches</h2>
            <p className="text-sm text-muted-foreground">
              Review and confirm detected transfer pairs.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {selectedIds.size > 0 && (
              <>
                <span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkReject}
                  disabled={bulkReject.isPending}
                  className="gap-1"
                >
                  <X className="h-3.5 w-3.5" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  onClick={handleBulkConfirm}
                  disabled={bulkConfirm.isPending}
                  className="gap-1"
                >
                  <Check className="h-3.5 w-3.5" />
                  Confirm All
                </Button>
              </>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  <ArrowUpDown className="h-3.5 w-3.5" />
                  Sort
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuRadioGroup
                  value={sortBy}
                  onValueChange={(v) => setSortBy(v as SortOption)}
                >
                  <DropdownMenuRadioItem value="confidence-desc">Confidence (High to Low)</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="confidence-asc">Confidence (Low to High)</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="amount-desc">Amount (High to Low)</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="amount-asc">Amount (Low to High)</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="date-desc">Date (Newest)</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="date-asc">Date (Oldest)</DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {suggestionsLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : sortedSuggestions.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-3" />
              <h3 className="text-lg font-medium mb-1">All caught up!</h3>
              <p className="text-sm text-muted-foreground">
                No pending transfer matches to review.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-3 px-4 py-2 bg-muted/30 rounded-lg">
              <Checkbox
                checked={selectedIds.size === sortedSuggestions.length && sortedSuggestions.length > 0}
                onCheckedChange={handleSelectAll}
              />
              <span className="text-sm text-muted-foreground">
                Select all ({sortedSuggestions.length} matches)
              </span>
            </div>

            {sortedSuggestions.map((match: any, i: number) => {
              const matchId = `${match.left_id || match.left?.id}:${match.right_id || match.right?.id}`
              return (
                <TransferCard
                  key={match.group_id || matchId || i}
                  match={match}
                  isSelected={selectedIds.has(matchId)}
                  onSelect={(checked) => {
                    setSelectedIds((prev) => {
                      const next = new Set(prev)
                      if (checked) next.add(matchId)
                      else next.delete(matchId)
                      return next
                    })
                  }}
                  onConfirm={() =>
                    handleConfirm(match.left_id || match.left?.id, match.right_id || match.right?.id)
                  }
                  onReject={() =>
                    handleReject(match.left_id || match.left?.id, match.right_id || match.right?.id)
                  }
                  isConfirming={confirmTransfer.isPending}
                  isRejecting={rejectTransfer.isPending}
                />
              )
            })}
          </div>
        )}
      </div>

      {/* Confirmed Transfers */}
      {confirmed && confirmed.length > 0 && (
        <div>
          <Button
            variant="ghost"
            className="flex items-center gap-2 mb-2 px-0 hover:bg-transparent"
            onClick={() => setShowConfirmed(!showConfirmed)}
          >
            {showConfirmed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            <span className="text-lg font-semibold">Confirmed Transfers ({confirmed.length})</span>
          </Button>

          {showConfirmed && (
            <Card>
              <CardContent className="p-0">
                <div className="divide-y">
                  {confirmedLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin" />
                    </div>
                  ) : (
                    confirmed.slice(0, 20).map((transfer: any, i: number) => (
                      <div key={transfer.group_id || i} className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <CheckCircle className="h-5 w-5 text-green-500" />
                          <div>
                            <div className="font-medium text-sm">
                              {transfer.left_desc || transfer.description || "Transfer"}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {transfer.left_date || transfer.decided_at || "-"}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">{formatAmount(transfer.left_amount || 0)}</div>
                          <div className="text-xs text-muted-foreground">
                            {transfer.left_account_id?.slice(-8)} → {transfer.right_account_id?.slice(-8)}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
