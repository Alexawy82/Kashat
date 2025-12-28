"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { GitMerge, Loader2, Check, ArrowRight } from "lucide-react"
import type { Counterparty } from "@/hooks/useP2P"

interface MergeDialogProps {
  sourceCounterparty: Counterparty | null
  allCounterparties: Counterparty[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onMerge: (sourceId: string, targetId: string) => Promise<void>
  isMerging: boolean
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))
}

export function MergeDialog({
  sourceCounterparty,
  allCounterparties,
  open,
  onOpenChange,
  onMerge,
  isMerging,
}: MergeDialogProps) {
  const [selectedTarget, setSelectedTarget] = useState<Counterparty | null>(null)
  const [search, setSearch] = useState("")

  // Filter out the source counterparty and filter by search
  const availableTargets = allCounterparties.filter(
    (cp) =>
      cp.id !== sourceCounterparty?.id &&
      (search === "" ||
        cp.name.toLowerCase().includes(search.toLowerCase()) ||
        cp.aliases?.some((a) => a.toLowerCase().includes(search.toLowerCase())))
  )

  const handleMerge = async () => {
    if (!sourceCounterparty || !selectedTarget) return
    await onMerge(sourceCounterparty.id, selectedTarget.id)
    setSelectedTarget(null)
    setSearch("")
    onOpenChange(false)
  }

  const handleClose = () => {
    setSelectedTarget(null)
    setSearch("")
    onOpenChange(false)
  }

  if (!sourceCounterparty) return null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5" />
            Merge Counterparties
          </DialogTitle>
          <DialogDescription>
            Merge <strong>{sourceCounterparty.name}</strong> into another counterparty.
            All transactions will be consolidated.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Source (will be deleted) */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="text-xs text-red-600 mb-1">Will be merged (deleted):</div>
            <div className="font-medium">{sourceCounterparty.name}</div>
            <div className="text-xs text-muted-foreground">
              {sourceCounterparty.transaction_count} transactions • {formatAmount(sourceCounterparty.total_sent + sourceCounterparty.total_received)}
            </div>
          </div>

          <div className="flex justify-center">
            <ArrowRight className="h-5 w-5 text-muted-foreground" />
          </div>

          {/* Target Selection */}
          <div>
            <div className="text-sm mb-2">Merge into:</div>
            <Command className="border rounded-lg">
              <CommandInput
                placeholder="Search counterparties..."
                value={search}
                onValueChange={setSearch}
              />
              <CommandList className="max-h-[200px]">
                <CommandEmpty>No counterparties found.</CommandEmpty>
                <CommandGroup>
                  {availableTargets.slice(0, 20).map((cp) => (
                    <CommandItem
                      key={cp.id}
                      value={cp.name}
                      onSelect={() => setSelectedTarget(cp)}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        {selectedTarget?.id === cp.id && (
                          <Check className="h-4 w-4 text-primary" />
                        )}
                        <span>{cp.name}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {cp.transaction_count} tx
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </div>

          {/* Selected Target Preview */}
          {selectedTarget && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="text-xs text-green-600 mb-1">Will keep (target):</div>
              <div className="font-medium">{selectedTarget.name}</div>
              <div className="text-xs text-muted-foreground">
                {selectedTarget.transaction_count} transactions • {formatAmount(selectedTarget.total_sent + selectedTarget.total_received)}
              </div>
              {selectedTarget.aliases && selectedTarget.aliases.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {selectedTarget.aliases.map((alias, i) => (
                    <Badge key={i} variant="outline" className="text-[10px]">
                      {alias}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isMerging}>
            Cancel
          </Button>
          <Button
            onClick={handleMerge}
            disabled={!selectedTarget || isMerging}
            className="gap-2"
          >
            {isMerging ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Merging...
              </>
            ) : (
              <>
                <GitMerge className="h-4 w-4" />
                Merge
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
