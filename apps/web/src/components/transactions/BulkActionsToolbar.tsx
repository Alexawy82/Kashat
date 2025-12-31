'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import {
  X,
  Tags,
  Trash2,
  Briefcase,
  TrendingUp,
  ChevronDown,
  Loader2,
  CheckCircle2,
} from 'lucide-react'
import { useCategories } from '@/hooks/useCategories'
import { useBulkUpdateTransactions, useBulkDeleteTransactions } from '@/hooks/useTransactions'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils'

interface BulkActionsToolbarProps {
  selectedIds: string[]
  onClearSelection: () => void
  selectedTransactions?: Array<{ id: string; is_business?: boolean; is_income?: boolean }>
}

export function BulkActionsToolbar({
  selectedIds,
  onClearSelection,
  selectedTransactions = [],
}: BulkActionsToolbarProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [actionResult, setActionResult] = useState<string | null>(null)

  const { data: categories = [] } = useCategories()
  const bulkUpdate = useBulkUpdateTransactions()
  const bulkDelete = useBulkDeleteTransactions()

  const count = selectedIds.length
  if (count === 0) return null

  const showActionResult = (message: string) => {
    setActionResult(message)
    setTimeout(() => setActionResult(null), 3000)
  }

  const handleBulkCategorize = (categoryId: string, categoryName: string) => {
    bulkUpdate.mutate(
      { ids: selectedIds, updates: { category_id: categoryId } },
      {
        onSuccess: () => {
          showActionResult(`Categorized ${count} transactions as "${categoryName}"`)
          onClearSelection()
        },
      }
    )
  }

  const handleBulkToggleBusiness = () => {
    // If any are not business, mark all as business. Otherwise, unmark all.
    const anyNotBusiness = selectedTransactions.some((t) => !t.is_business)
    bulkUpdate.mutate(
      { ids: selectedIds, updates: { is_business: anyNotBusiness } },
      {
        onSuccess: () => {
          showActionResult(
            anyNotBusiness
              ? `Marked ${count} transactions as business`
              : `Unmarked ${count} transactions as business`
          )
          onClearSelection()
        },
      }
    )
  }

  const handleBulkToggleIncome = () => {
    // If any are not income, mark all as income. Otherwise, unmark all.
    const anyNotIncome = selectedTransactions.some((t) => !t.is_income)
    bulkUpdate.mutate(
      { ids: selectedIds, updates: { is_income: anyNotIncome } },
      {
        onSuccess: () => {
          showActionResult(
            anyNotIncome
              ? `Marked ${count} transactions as income`
              : `Unmarked ${count} transactions as income`
          )
          onClearSelection()
        },
      }
    )
  }

  const handleBulkDelete = () => {
    bulkDelete.mutate(
      { ids: selectedIds },
      {
        onSuccess: () => {
          showActionResult(`Deleted ${count} transactions`)
          onClearSelection()
          setShowDeleteConfirm(false)
        },
      }
    )
  }

  const isLoading = bulkUpdate.isPending || bulkDelete.isPending

  return (
    <>
      <div
        className={cn(
          'flex items-center gap-3 p-3 bg-primary/5 border border-primary/20 rounded-lg',
          'animate-in slide-in-from-top-2 duration-200'
        )}
      >
        {/* Selection Count */}
        <div className="flex items-center gap-2">
          <Badge variant="default" className="px-3 py-1">
            {count} selected
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            className="h-7 px-2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="h-6 w-px bg-border" />

        {/* Categorize Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2" disabled={isLoading}>
              <Tags className="h-4 w-4" />
              Categorize
              <ChevronDown className="h-3 w-3 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-64 overflow-y-auto">
            {categories.map((cat: any) => (
              <DropdownMenuItem
                key={cat.id}
                onClick={() => handleBulkCategorize(cat.id, cat.name)}
              >
                {cat.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Mark as Business */}
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleBulkToggleBusiness}
          disabled={isLoading}
        >
          <Briefcase className="h-4 w-4" />
          Toggle Business
        </Button>

        {/* Mark as Income */}
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleBulkToggleIncome}
          disabled={isLoading}
        >
          <TrendingUp className="h-4 w-4" />
          Toggle Income
        </Button>

        <div className="flex-1" />

        {/* Delete */}
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-destructive hover:text-destructive hover:bg-destructive/10"
          onClick={() => setShowDeleteConfirm(true)}
          disabled={isLoading}
        >
          <Trash2 className="h-4 w-4" />
          Delete
        </Button>

        {/* Loading indicator */}
        {isLoading && <Loader2 className="h-4 w-4 animate-spin text-primary" />}

        {/* Keyboard hint */}
        <span className="text-xs text-muted-foreground hidden md:inline">
          Esc to clear
        </span>
      </div>

      {/* Action Result Toast */}
      {actionResult && (
        <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm animate-in slide-in-from-top-2">
          <CheckCircle2 className="h-4 w-4" />
          {actionResult}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Transactions"
        description={`Are you sure you want to delete ${count} transaction${count > 1 ? 's' : ''}? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={handleBulkDelete}
        loading={bulkDelete.isPending}
      />
    </>
  )
}
