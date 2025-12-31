'use client'

import { useState, useRef, useEffect } from 'react'
import { Check, ChevronDown, Sparkles, Clock, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useCategories } from '@/hooks/useCategories'
import { useSetTransactionCategory } from '@/hooks/useTransactions'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

interface InlineCategorySelectorProps {
  transactionId: string
  currentCategory?: string | null
  currentCategoryId?: string | null
  aiSuggestedCategory?: string | null
  aiConfidence?: number | null
  onCategoryChange?: (categoryId: string, categoryName: string) => void
  disabled?: boolean
  compact?: boolean
}

export function InlineCategorySelector({
  transactionId,
  currentCategory,
  currentCategoryId,
  aiSuggestedCategory,
  aiConfidence,
  onCategoryChange,
  disabled = false,
  compact = false,
}: InlineCategorySelectorProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: categories = [] } = useCategories()
  const setCategory = useSetTransactionCategory()

  // Focus search input when popover opens
  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  // Filter categories based on search
  const filteredCategories = categories.filter((cat: any) =>
    cat.name.toLowerCase().includes(search.toLowerCase())
  )

  // Get recently used categories (top 5 by usage)
  const recentCategories = categories
    .filter((cat: any) => cat.transaction_count > 0)
    .sort((a: any, b: any) => (b.transaction_count || 0) - (a.transaction_count || 0))
    .slice(0, 5)

  const handleSelect = async (categoryId: string, categoryName: string) => {
    setOpen(false)
    setSearch('')

    if (onCategoryChange) {
      onCategoryChange(categoryId, categoryName)
    } else {
      // Default behavior: use the mutation
      setCategory.mutate({
        txId: transactionId,
        categoryId,
        categoryName,
      })
    }
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    // Clear category - set to empty
    if (onCategoryChange) {
      onCategoryChange('', '')
    }
  }

  const isUncategorized = !currentCategory && !currentCategoryId

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          disabled={disabled || setCategory.isPending}
          className={cn(
            'h-7 px-2 justify-start font-normal',
            compact ? 'text-xs' : 'text-sm',
            isUncategorized && 'text-muted-foreground italic'
          )}
        >
          {setCategory.isPending ? (
            <span className="animate-pulse">Saving...</span>
          ) : (
            <>
              <span className="truncate max-w-[120px]">
                {currentCategory || 'Uncategorized'}
              </span>
              {currentCategory && (
                <X
                  className="h-3 w-3 ml-1 opacity-50 hover:opacity-100"
                  onClick={handleClear}
                />
              )}
              <ChevronDown className="h-3 w-3 ml-1 opacity-50" />
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-0" align="start">
        {/* Search */}
        <div className="p-2 border-b">
          <Input
            ref={inputRef}
            placeholder="Search categories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 text-sm"
          />
        </div>

        <div className="max-h-[300px] overflow-y-auto">
          {/* AI Suggestion */}
          {aiSuggestedCategory && !search && (
            <div className="p-2 border-b bg-muted/30">
              <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-purple-500" />
                AI Suggestion
                {aiConfidence && (
                  <span className="text-[10px] opacity-60">
                    ({Math.round(aiConfidence * 100)}%)
                  </span>
                )}
              </p>
              <button
                className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-purple-100 dark:hover:bg-purple-900/30 flex items-center justify-between"
                onClick={() => {
                  const cat = categories.find((c: any) => c.name === aiSuggestedCategory)
                  if (cat) {
                    handleSelect(cat.id, cat.name)
                  }
                }}
              >
                <span>{aiSuggestedCategory}</span>
                <Badge variant="outline" className="text-[10px] h-4 px-1 bg-purple-100 border-purple-200 text-purple-700">
                  Apply
                </Badge>
              </button>
            </div>
          )}

          {/* Recent Categories */}
          {recentCategories.length > 0 && !search && (
            <div className="p-2 border-b">
              <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Recent
              </p>
              <div className="flex flex-wrap gap-1">
                {recentCategories.map((cat: any) => (
                  <button
                    key={cat.id}
                    className={cn(
                      'px-2 py-0.5 rounded text-xs hover:bg-accent',
                      currentCategoryId === cat.id && 'bg-accent font-medium'
                    )}
                    onClick={() => handleSelect(cat.id, cat.name)}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* All Categories */}
          <div className="p-1">
            {filteredCategories.length === 0 ? (
              <p className="text-sm text-muted-foreground p-2 text-center">
                No categories found
              </p>
            ) : (
              filteredCategories.map((cat: any) => (
                <button
                  key={cat.id}
                  className={cn(
                    'w-full text-left px-2 py-1.5 rounded text-sm hover:bg-accent flex items-center justify-between',
                    currentCategoryId === cat.id && 'bg-accent'
                  )}
                  onClick={() => handleSelect(cat.id, cat.name)}
                >
                  <span className="truncate">{cat.name}</span>
                  {currentCategoryId === cat.id && (
                    <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                  )}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Keyboard hint */}
        <div className="p-2 border-t bg-muted/30">
          <p className="text-[10px] text-muted-foreground text-center">
            Type to search • Enter to select • Esc to close
          </p>
        </div>
      </PopoverContent>
    </Popover>
  )
}
