"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

export type ServiceFilter = "all" | "zelle" | "venmo" | "cashapp" | "paypal" | "wire" | "western_union"
export type TypeFilter = "all" | "person" | "business"
export type SortOption = "amount" | "transactions" | "recent" | "name"

interface CounterpartyFiltersProps {
  service: ServiceFilter
  onServiceChange: (value: ServiceFilter) => void
  type: TypeFilter
  onTypeChange: (value: TypeFilter) => void
  recurringOnly: boolean
  onRecurringOnlyChange: (value: boolean) => void
  sortBy: SortOption
  onSortChange: (value: SortOption) => void
}

const SERVICES: { value: ServiceFilter; label: string }[] = [
  { value: "all", label: "All Services" },
  { value: "zelle", label: "Zelle" },
  { value: "venmo", label: "Venmo" },
  { value: "cashapp", label: "Cash App" },
  { value: "paypal", label: "PayPal" },
  { value: "wire", label: "Wire" },
  { value: "western_union", label: "Western Union" },
]

const TYPES: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "All Types" },
  { value: "person", label: "People" },
  { value: "business", label: "Businesses" },
]

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "amount", label: "Total Amount" },
  { value: "transactions", label: "Transaction Count" },
  { value: "recent", label: "Most Recent" },
  { value: "name", label: "Name A-Z" },
]

export function CounterpartyFilters({
  service,
  onServiceChange,
  type,
  onTypeChange,
  recurringOnly,
  onRecurringOnlyChange,
  sortBy,
  onSortChange,
}: CounterpartyFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 p-4 bg-muted/30 rounded-lg">
      {/* Service Filter */}
      <div className="flex items-center gap-2">
        <Label className="text-sm text-muted-foreground shrink-0">Service:</Label>
        <Select value={service} onValueChange={(v) => onServiceChange(v as ServiceFilter)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SERVICES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Type Filter */}
      <div className="flex items-center gap-2">
        <Label className="text-sm text-muted-foreground shrink-0">Type:</Label>
        <Select value={type} onValueChange={(v) => onTypeChange(v as TypeFilter)}>
          <SelectTrigger className="w-[120px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TYPES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Recurring Toggle */}
      <div className="flex items-center gap-2">
        <Switch
          id="recurring-only"
          checked={recurringOnly}
          onCheckedChange={onRecurringOnlyChange}
        />
        <Label htmlFor="recurring-only" className="text-sm cursor-pointer">
          Recurring Only
        </Label>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Sort */}
      <div className="flex items-center gap-2">
        <Label className="text-sm text-muted-foreground shrink-0">Sort:</Label>
        <Select value={sortBy} onValueChange={(v) => onSortChange(v as SortOption)}>
          <SelectTrigger className="w-[150px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
