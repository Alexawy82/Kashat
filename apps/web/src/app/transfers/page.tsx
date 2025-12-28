"use client"

import { useMemo, useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Users, ArrowRightLeft, Loader2 } from "lucide-react"
import {
  useP2PStats,
  useCounterparties,
  useEnrichmentStats,
  useDetectP2P,
  useEnrichP2P,
  useMergeCounterparties,
  type Counterparty,
} from "@/hooks/useP2P"

// Components
import { StatsCards } from "./components/StatsCards"
import { CounterpartyCard } from "./components/CounterpartyCard"
import { CounterpartySheet } from "./components/CounterpartySheet"
import { CounterpartyFilters, type ServiceFilter, type TypeFilter, type SortOption } from "./components/CounterpartyFilters"
import { MergeDialog } from "./components/MergeDialog"
import { DetectionButtons } from "./components/DetectionButtons"
import { TransfersTab } from "./components/TransfersTab"

export default function TransfersPage() {
  // Tab state
  const [activeTab, setActiveTab] = useState("people")

  // Filters state
  const [serviceFilter, setServiceFilter] = useState<ServiceFilter>("all")
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all")
  const [recurringOnly, setRecurringOnly] = useState(false)
  const [sortBy, setSortBy] = useState<SortOption>("amount")

  // Sheet/Dialog state
  const [selectedCounterparty, setSelectedCounterparty] = useState<Counterparty | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [mergeDialogOpen, setMergeDialogOpen] = useState(false)
  const [mergeSource, setMergeSource] = useState<Counterparty | null>(null)

  // Data hooks
  const { data: stats, isLoading: statsLoading } = useP2PStats()
  const { data: counterparties, isLoading: counterpartiesLoading } = useCounterparties({
    recurring_only: recurringOnly,
    limit: 200,
  })
  const { data: enrichmentStats } = useEnrichmentStats()

  // Mutations
  const detectP2P = useDetectP2P()
  const enrichP2P = useEnrichP2P()
  const mergeCounterparties = useMergeCounterparties()

  // Filter and sort counterparties client-side
  const filteredCounterparties = useMemo(() => {
    if (!counterparties) return []

    let filtered = [...counterparties]

    // Filter by service - client-side (check if name contains service pattern)
    // This is a workaround since the API doesn't support service filtering yet
    // In production, you'd want to add this to the backend

    // Filter by type (person vs business) - heuristic based on name
    if (typeFilter === "person") {
      filtered = filtered.filter((cp) => {
        // Names that are all uppercase and don't have spaces are likely businesses
        const isLikelyBusiness =
          cp.name.toUpperCase() === cp.name &&
          cp.name.length > 3 &&
          !cp.name.includes(" ")
        return !isLikelyBusiness
      })
    } else if (typeFilter === "business") {
      filtered = filtered.filter((cp) => {
        const isLikelyBusiness =
          cp.name.toUpperCase() === cp.name &&
          cp.name.length > 3 &&
          !cp.name.includes(" ")
        return isLikelyBusiness
      })
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "amount":
          return (b.total_sent + b.total_received) - (a.total_sent + a.total_received)
        case "transactions":
          return b.transaction_count - a.transaction_count
        case "recent":
          return (b.last_seen || "").localeCompare(a.last_seen || "")
        case "name":
          return a.name.localeCompare(b.name)
        default:
          return 0
      }
    })

    return filtered
  }, [counterparties, serviceFilter, typeFilter, sortBy])

  // Calculate people count from stats
  const peopleCount = stats?.top_counterparties?.length || 0

  // Pipeline state
  const [isRunningPipeline, setIsRunningPipeline] = useState(false)

  // Handlers
  const handleDetect = (useAI: boolean) => {
    detectP2P.mutate({ use_ai: useAI })
  }

  const handleEnrich = () => {
    enrichP2P.mutate({})
  }

  // Simplified pipeline: Detect → Enrich
  // Recurring detection is handled by the regular recurring pipeline
  const handleFullPipeline = async () => {
    setIsRunningPipeline(true)
    try {
      // Step 1: Detect P2P with AI
      await detectP2P.mutateAsync({ use_ai: true })
      // Step 2: Enrich with AI
      await enrichP2P.mutateAsync({})
    } catch (err) {
      console.error("Pipeline error:", err)
    } finally {
      setIsRunningPipeline(false)
    }
  }

  const handleCounterpartyClick = (counterparty: Counterparty) => {
    setSelectedCounterparty(counterparty)
    setSheetOpen(true)
  }

  const handleMergeClick = (counterparty: Counterparty) => {
    setMergeSource(counterparty)
    setMergeDialogOpen(true)
    setSheetOpen(false)
  }

  const handleMerge = async (sourceId: string, targetId: string) => {
    await mergeCounterparties.mutateAsync({ sourceId, targetId })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">People & Transfers</h1>
          <p className="text-muted-foreground mt-1">
            Track who you transact with and match internal transfers.
          </p>
        </div>
        <DetectionButtons
          onDetect={handleDetect}
          onEnrich={handleEnrich}
          isDetecting={detectP2P.isPending}
          isEnriching={enrichP2P.isPending}
          enrichmentStats={enrichmentStats}
          onRunFullPipeline={handleFullPipeline}
          isRunningPipeline={isRunningPipeline}
        />
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="people" className="gap-2">
            <Users className="h-4 w-4" />
            People
            {peopleCount > 0 && (
              <span className="ml-1 text-xs bg-muted px-1.5 py-0.5 rounded-full">
                {peopleCount}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="transfers" className="gap-2">
            <ArrowRightLeft className="h-4 w-4" />
            Internal Transfers
          </TabsTrigger>
        </TabsList>

        {/* People Tab */}
        <TabsContent value="people" className="space-y-6">
          {/* Stats Cards */}
          <StatsCards
            stats={stats}
            isLoading={statsLoading}
          />

          {/* Filters */}
          <CounterpartyFilters
            service={serviceFilter}
            onServiceChange={setServiceFilter}
            type={typeFilter}
            onTypeChange={setTypeFilter}
            recurringOnly={recurringOnly}
            onRecurringOnlyChange={setRecurringOnly}
            sortBy={sortBy}
            onSortChange={setSortBy}
          />

          {/* Counterparty List */}
          {counterpartiesLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredCounterparties.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium">No counterparties found</p>
              <p className="text-sm mt-1">
                {serviceFilter !== "all" || typeFilter !== "all" || recurringOnly
                  ? "Try adjusting your filters"
                  : "Run P2P detection to identify people you transact with"}
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {filteredCounterparties.map((cp) => (
                <CounterpartyCard
                  key={cp.id}
                  counterparty={cp}
                  onClick={() => handleCounterpartyClick(cp)}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* Internal Transfers Tab */}
        <TabsContent value="transfers">
          <TransfersTab />
        </TabsContent>
      </Tabs>

      {/* Detail Sheet */}
      <CounterpartySheet
        counterparty={selectedCounterparty}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onMerge={handleMergeClick}
      />

      {/* Merge Dialog */}
      <MergeDialog
        sourceCounterparty={mergeSource}
        allCounterparties={counterparties || []}
        open={mergeDialogOpen}
        onOpenChange={setMergeDialogOpen}
        onMerge={handleMerge}
        isMerging={mergeCounterparties.isPending}
      />
    </div>
  )
}
