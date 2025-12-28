"use client"

import { useState, useEffect } from "react"
import { DataTable } from "./data-table"
import { columns } from "./columns"
import { useTransactions, useTransactionStats } from "@/hooks/useTransactions"
import { useCategories, useCategorizeAllTransactions, useCategorizationStatus, useCategoryCoverage } from "@/hooks/useCategories"
import { useAccounts } from "@/hooks/useAccounts"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Loader2, AlertCircle, Sparkles, Briefcase, Tags,
  X, ChevronDown, CheckCircle2,
  Calendar, Building2, TrendingUp, Search,
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight
} from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { useDebounce } from "@/hooks/useDebounce"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type FilterType = 'all' | 'uncategorized' | 'business' | 'income'

// Generate page numbers to display
function getPageNumbers(current: number, total: number): (number | 'ellipsis')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }

  const pages: (number | 'ellipsis')[] = []

  if (current <= 4) {
    // Near start: 1 2 3 4 5 ... last
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('ellipsis')
    pages.push(total)
  } else if (current >= total - 3) {
    // Near end: 1 ... last-4 last-3 last-2 last-1 last
    pages.push(1)
    pages.push('ellipsis')
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    // Middle: 1 ... current-1 current current+1 ... last
    pages.push(1)
    pages.push('ellipsis')
    pages.push(current - 1)
    pages.push(current)
    pages.push(current + 1)
    pages.push('ellipsis')
    pages.push(total)
  }

  return pages
}

export default function TransactionsPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState("")
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [accountFilter, setAccountFilter] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<string>("")
  const [endDate, setEndDate] = useState<string>("")

  useEffect(() => {
    try {
      const url = new URL(window.location.href)
      const q = url.searchParams.get("q") || ""
      setSearch(q)
      setPage(1)
    } catch {
      // ignore
    }
  }, [])

  const debouncedSearch = useDebounce(search, 500)

  const filter = {
    page,
    limit: pageSize,
    search: debouncedSearch,
    sortBy: 'date',
    sortDir: 'desc' as const,
    uncategorized: activeFilter === 'uncategorized' ? true : undefined,
    isBusiness: activeFilter === 'business' ? true : undefined,
    isIncome: activeFilter === 'income' ? true : undefined,
    categoryId: categoryFilter || undefined,
    accountId: accountFilter || undefined,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
  }

  const { data, isLoading, isError, isFetching } = useTransactions(filter)
  const { data: categories } = useCategories()
  const { data: accounts } = useAccounts()

  const { data: uncategorizedStats } = useTransactionStats({ uncategorized: true })
  const { data: businessStats } = useTransactionStats({ isBusiness: true })
  const { data: incomeStats } = useTransactionStats({ isIncome: true })

  const categorizeAll = useCategorizeAllTransactions()
  const { data: categorizationStatus } = useCategorizationStatus()
  const { data: coverage } = useCategoryCoverage()

  // Check if a categorization job is running
  const isCategorizationRunning = categorizationStatus?.current_job?.status === 'processing'

  const [actionResult, setActionResult] = useState<string | null>(null)

  const handleFilterChange = (newFilter: FilterType) => {
    setActiveFilter(newFilter)
    setCategoryFilter(null)
    setPage(1)
  }

  const handleCategoryFilter = (catId: string | null) => {
    setCategoryFilter(catId)
    setActiveFilter('all')
    setPage(1)
  }

  const handleAccountFilter = (accId: string | null) => {
    setAccountFilter(accId)
    setPage(1)
  }

  const handlePageSizeChange = (size: string) => {
    setPageSize(parseInt(size))
    setPage(1)
  }

  const clearAllFilters = () => {
    setActiveFilter('all')
    setCategoryFilter(null)
    setAccountFilter(null)
    setStartDate('')
    setEndDate('')
    setSearch('')
    setPage(1)
  }

  const hasActiveFilters = activeFilter !== 'all' || categoryFilter !== null || accountFilter !== null || search !== '' || startDate !== '' || endDate !== ''
  const totalPages = data?.total_pages || 1
  const uncategorizedCount = uncategorizedStats?.total || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
          <div className="flex items-center gap-4 mt-1">
            {data?.total !== undefined && (
              <span className="text-sm text-muted-foreground">
                {data.total.toLocaleString()} transactions
              </span>
            )}
            {coverage && (
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-24 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full transition-all"
                    style={{ width: `${coverage.coverage_percent || 0}%` }}
                  />
                </div>
                <span className="text-sm text-muted-foreground">
                  {coverage.coverage_percent?.toFixed(0)}% categorized
                </span>
              </div>
            )}
          </div>
        </div>

        {/* AI Action - Show categorization button or progress */}
        {isCategorizationRunning ? (
          <div className="flex items-center gap-3 bg-primary/10 rounded-lg px-4 py-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <div className="flex flex-col">
              <span className="text-sm font-medium">
                Categorizing... {categorizationStatus?.current_job?.progress_percent?.toFixed(0)}%
              </span>
              <span className="text-xs text-muted-foreground">
                {categorizationStatus?.current_job?.processed || 0} / {categorizationStatus?.current_job?.total || 0} transactions
              </span>
            </div>
            <div className="h-2 w-24 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${categorizationStatus?.current_job?.progress_percent || 0}%` }}
              />
            </div>
          </div>
        ) : uncategorizedCount > 0 ? (
          <Button
            variant="default"
            size="sm"
            className="gap-2"
            onClick={() => {
              categorizeAll.mutate({ batch_size: 50 }, {
                onSuccess: (data) => {
                  if (data.status === 'started') {
                    setActionResult(`Started categorizing ${data.total_transactions} transactions...`)
                  } else if (data.status === 'already_running') {
                    setActionResult('A categorization job is already running')
                  } else {
                    setActionResult('No uncategorized transactions')
                  }
                  setTimeout(() => setActionResult(null), 5000)
                }
              })
            }}
            disabled={categorizeAll.isPending}
          >
            {categorizeAll.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Auto-Categorize
            <Badge variant="secondary" className="ml-1 bg-white/20">
              {uncategorizedCount}
            </Badge>
          </Button>
        ) : null}
      </div>

      {/* Action Result Toast */}
      {actionResult && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-700">{actionResult}</AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <div className="space-y-3 p-4 bg-muted/30 rounded-lg border">
        {/* Row 1: Search + Dropdowns */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search transactions..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="w-72 pl-9 bg-background"
            />
          </div>

          {/* Category */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2 bg-background">
                <Tags className="h-4 w-4" />
                {categoryFilter
                  ? categories?.find((c: any) => c.id === categoryFilter)?.name || 'Category'
                  : 'All Categories'}
                <ChevronDown className="h-3 w-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="max-h-72 overflow-y-auto">
              <DropdownMenuItem onClick={() => handleCategoryFilter(null)}>
                All Categories
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {categories?.map((cat: any) => (
                <DropdownMenuItem key={cat.id} onClick={() => handleCategoryFilter(cat.id)}>
                  {cat.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Account */}
          {accounts && accounts.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2 bg-background">
                  <Building2 className="h-4 w-4" />
                  {accountFilter
                    ? accounts.find(a => a.id === accountFilter)?.name || 'Account'
                    : 'All Accounts'}
                  <ChevronDown className="h-3 w-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => handleAccountFilter(null)}>
                  All Accounts
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                {accounts.map((acc) => (
                  <DropdownMenuItem key={acc.id} onClick={() => handleAccountFilter(acc.id)}>
                    {acc.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {/* Date Range */}
          <div className="flex items-center gap-2 ml-auto">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <Input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
              className="w-36 h-9 bg-background"
            />
            <span className="text-muted-foreground text-sm">to</span>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
              className="w-36 h-9 bg-background"
            />
          </div>
        </div>

        {/* Row 2: Quick Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant={activeFilter === 'all' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => handleFilterChange('all')}
            className="h-8"
          >
            All
          </Button>

          <Button
            variant={activeFilter === 'uncategorized' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => handleFilterChange('uncategorized')}
            className="h-8 gap-1.5"
          >
            <Tags className="h-3.5 w-3.5" />
            Uncategorized
            {uncategorizedCount > 0 && (
              <Badge variant={activeFilter === 'uncategorized' ? 'secondary' : 'outline'} className="text-[10px] px-1.5 h-5">
                {uncategorizedCount}
              </Badge>
            )}
          </Button>

          <Button
            variant={activeFilter === 'income' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => handleFilterChange('income')}
            className="h-8 gap-1.5"
          >
            <TrendingUp className="h-3.5 w-3.5" />
            Income
            {(incomeStats?.total || 0) > 0 && (
              <Badge variant={activeFilter === 'income' ? 'secondary' : 'outline'} className="text-[10px] px-1.5 h-5">
                {incomeStats?.total}
              </Badge>
            )}
          </Button>

          <Button
            variant={activeFilter === 'business' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => handleFilterChange('business')}
            className="h-8 gap-1.5"
          >
            <Briefcase className="h-3.5 w-3.5" />
            Business
            {(businessStats?.total || 0) > 0 && (
              <Badge variant={activeFilter === 'business' ? 'secondary' : 'outline'} className="text-[10px] px-1.5 h-5">
                {businessStats?.total}
              </Badge>
            )}
          </Button>

          {hasActiveFilters && (
            <>
              <div className="h-4 w-px bg-border mx-1" />
              <Button variant="ghost" size="sm" onClick={clearAllFilters} className="h-8 gap-1 text-muted-foreground hover:text-foreground">
                <X className="h-3.5 w-3.5" />
                Clear filters
              </Button>
            </>
          )}

          {isFetching && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground ml-2" />
          )}
        </div>
      </div>

      {/* Table */}
      {isError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load transactions. Please check your connection.
          </AlertDescription>
        </Alert>
      ) : (isLoading || isFetching) && !data?.items?.length ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 bg-muted/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : !data?.items?.length ? (
        <div className="text-center py-16 border rounded-lg bg-muted/20">
          <Tags className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-medium mb-1">No transactions found</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {hasActiveFilters
              ? "Try adjusting your filters or search terms"
              : "Import some transactions to get started"}
          </p>
          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={clearAllFilters}>
              Clear all filters
            </Button>
          )}
        </div>
      ) : (
        <>
          <DataTable columns={columns} data={data?.items || []} />

          {/* Pagination */}
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {((page - 1) * pageSize) + 1}-{Math.min(page * pageSize, data?.total || 0)} of {data?.total?.toLocaleString()}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Show</span>
                <Select value={pageSize.toString()} onValueChange={handlePageSizeChange}>
                  <SelectTrigger className="w-16 h-8">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Page Navigation */}
            <div className="flex items-center gap-1">
              {/* First Page */}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setPage(1)}
                disabled={page === 1}
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>

              {/* Previous */}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              {/* Page Numbers */}
              <div className="flex items-center gap-1 mx-1">
                {getPageNumbers(page, totalPages).map((p, idx) => (
                  p === 'ellipsis' ? (
                    <span key={`ellipsis-${idx}`} className="px-2 text-muted-foreground">...</span>
                  ) : (
                    <Button
                      key={p}
                      variant={page === p ? 'default' : 'ghost'}
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={() => setPage(p)}
                    >
                      {p}
                    </Button>
                  )
                ))}
              </div>

              {/* Next */}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>

              {/* Last Page */}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setPage(totalPages)}
                disabled={page >= totalPages}
              >
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
