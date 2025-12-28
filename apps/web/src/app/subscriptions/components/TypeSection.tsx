'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu'
import { SeriesCard } from '@/app/subscriptions/components/SeriesCard'
import { formatAmount, RecurringSeries, sumMonthly } from '@/app/subscriptions/lib/recurringUtils'
import {
  ArrowDownAZ,
  ArrowUpDown,
  Filter,
  CreditCard,
  Home,
  Landmark,
  Shield,
  Tv,
  Layers,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'

type SortOption = 'amount-desc' | 'amount-asc' | 'name' | 'next-date' | 'status'
type FilterStatus = 'all' | 'active' | 'overdue' | 'likely_cancelled'

const tabIcons: Record<string, typeof Tv> = {
  all: Layers,
  subscriptions: Tv,
  bills: Home,
  loans: Landmark,
  'credit-cards': CreditCard,
  insurance: Shield,
}

const tabColors: Record<string, string> = {
  all: 'text-primary',
  subscriptions: 'text-purple-600',
  bills: 'text-blue-600',
  loans: 'text-amber-600',
  'credit-cards': 'text-green-600',
  insurance: 'text-red-600',
}

export function TypeSection({
  title,
  description,
  items,
  isLoading,
  onSelect,
  tabKey,
}: {
  title: string
  description?: string
  items: RecurringSeries[]
  isLoading?: boolean
  onSelect?: (item: RecurringSeries) => void
  tabKey?: string
}) {
  const [sortBy, setSortBy] = useState<SortOption>('amount-desc')
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [showEssentialOnly, setShowEssentialOnly] = useState(false)

  const Icon = tabKey ? tabIcons[tabKey] || Layers : Layers
  const colorClass = tabKey ? tabColors[tabKey] || 'text-primary' : 'text-primary'

  // Calculate stats
  const stats = useMemo(() => {
    const active = items.filter((i) => i.status === 'active').length
    const overdue = items.filter((i) => i.status === 'overdue').length
    const essential = items.filter((i) => i.is_essential).length
    return { active, overdue, essential }
  }, [items])

  // Filter and sort items
  const displayItems = useMemo(() => {
    let filtered = [...items]

    // Apply status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter((item) => item.status === filterStatus)
    }

    // Apply essential filter
    if (showEssentialOnly) {
      filtered = filtered.filter((item) => item.is_essential)
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'amount-desc':
          return Math.abs(b.amount_mean || 0) - Math.abs(a.amount_mean || 0)
        case 'amount-asc':
          return Math.abs(a.amount_mean || 0) - Math.abs(b.amount_mean || 0)
        case 'name':
          return (a.merchant_name || a.name || '').localeCompare(b.merchant_name || b.name || '')
        case 'next-date':
          const dateA = a.next_date || '9999-99-99'
          const dateB = b.next_date || '9999-99-99'
          return dateA.localeCompare(dateB)
        case 'status':
          const statusOrder = { overdue: 0, active: 1, likely_cancelled: 2 }
          const orderA = statusOrder[a.status as keyof typeof statusOrder] ?? 3
          const orderB = statusOrder[b.status as keyof typeof statusOrder] ?? 3
          return orderA - orderB
        default:
          return 0
      }
    })

    return filtered
  }, [items, sortBy, filterStatus, showEssentialOnly])

  const totalMonthly = sumMonthly(displayItems)
  const totalAnnual = totalMonthly * 12
  const hasActiveFilters = filterStatus !== 'all' || showEssentialOnly

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg bg-muted ${colorClass}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">{title}</CardTitle>
              {description && <CardDescription>{description}</CardDescription>}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {stats.active > 0 && (
                  <Badge variant="outline" className="text-green-600 border-green-200 text-[10px]">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    {stats.active} active
                  </Badge>
                )}
                {stats.overdue > 0 && (
                  <Badge variant="outline" className="text-red-600 border-red-200 text-[10px]">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {stats.overdue} overdue
                  </Badge>
                )}
                {stats.essential > 0 && (
                  <Badge variant="secondary" className="text-[10px]">
                    {stats.essential} essential
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">{formatAmount(totalMonthly)}</div>
            <div className="text-xs text-muted-foreground">/month</div>
            <div className="text-sm text-muted-foreground mt-1">{formatAmount(totalAnnual)}/year</div>
          </div>
        </div>

        {/* Sort & Filter Controls */}
        <div className="flex items-center gap-2 mt-4 pt-3 border-t">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 gap-2">
                <ArrowUpDown className="h-3.5 w-3.5" />
                Sort
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuRadioGroup value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
                <DropdownMenuRadioItem value="amount-desc">Amount (High → Low)</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="amount-asc">Amount (Low → High)</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="name">Name (A → Z)</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="next-date">Next Due Date</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="status">Status</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant={hasActiveFilters ? 'default' : 'outline'} size="sm" className="h-8 gap-2">
                <Filter className="h-3.5 w-3.5" />
                Filter
                {hasActiveFilters && (
                  <Badge variant="secondary" className="ml-1 h-4 px-1 text-[10px]">
                    Active
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuRadioGroup value={filterStatus} onValueChange={(v) => setFilterStatus(v as FilterStatus)}>
                <DropdownMenuRadioItem value="all">All Status</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="active">Active Only</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="overdue">Overdue Only</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="likely_cancelled">Likely Cancelled</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
              <DropdownMenuSeparator />
              <DropdownMenuCheckboxItem
                checked={showEssentialOnly}
                onCheckedChange={setShowEssentialOnly}
              >
                Essential Only
              </DropdownMenuCheckboxItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs"
              onClick={() => {
                setFilterStatus('all')
                setShowEssentialOnly(false)
              }}
            >
              Clear filters
            </Button>
          )}

          <span className="text-xs text-muted-foreground ml-auto">
            Showing {displayItems.length} of {items.length}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-sm text-muted-foreground py-8 text-center">Loading…</div>
        ) : displayItems.length === 0 ? (
          <div className="text-sm text-muted-foreground py-8 text-center">
            {hasActiveFilters ? 'No items match your filters.' : 'No recurring items found.'}
          </div>
        ) : (
          <div className="grid gap-2">
            {displayItems.map((item) => (
              <SeriesCard key={item.id || item.series_id} item={item} onSelect={onSelect} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
