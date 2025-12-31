"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  MoreHorizontal,
  Tags,
  Store,
  Briefcase,
  TrendingUp,
  Trash2,
  Loader2,
  AlertTriangle,
} from "lucide-react"
import { useCategories } from "@/hooks/useCategories"
import {
  useDeleteTransaction,
  useUpdateTransaction,
  useSetTransactionCategory,
} from "@/hooks/useTransactions"

interface Transaction {
  id: string
  merchant?: string
  description?: string
  category?: string
  category_id?: string
  is_business?: boolean
  is_income?: boolean
}

interface TransactionActionsProps {
  transaction: Transaction
}

export function TransactionActions({ transaction }: TransactionActionsProps) {
  const [showCategoryDialog, setShowCategoryDialog] = useState(false)
  const [showMerchantDialog, setShowMerchantDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState(transaction.category_id || "")
  const [merchantName, setMerchantName] = useState(transaction.merchant || "")

  const { data: categories } = useCategories()
  const deleteTransaction = useDeleteTransaction()
  const updateTransaction = useUpdateTransaction()
  const setCategory = useSetTransactionCategory()

  const handleToggleBusiness = () => {
    updateTransaction.mutate({
      txId: transaction.id,
      is_business: !transaction.is_business,
    })
  }

  const handleToggleIncome = () => {
    updateTransaction.mutate({
      txId: transaction.id,
      is_income: !transaction.is_income,
    })
  }

  const handleSetCategory = () => {
    if (selectedCategory) {
      const categoryName = categories?.find((c: any) => c.id === selectedCategory)?.name
      setCategory.mutate(
        { txId: transaction.id, categoryId: selectedCategory, categoryName },
        { onSuccess: () => setShowCategoryDialog(false) }
      )
    }
  }

  const handleSetMerchant = () => {
    updateTransaction.mutate(
      { txId: transaction.id, ai_merchant_name: merchantName || null },
      { onSuccess: () => setShowMerchantDialog(false) }
    )
  }

  const handleDelete = () => {
    deleteTransaction.mutate(transaction.id, {
      onSuccess: () => setShowDeleteDialog(false),
    })
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <span className="sr-only">Open menu</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onClick={() => setShowCategoryDialog(true)}>
            <Tags className="h-4 w-4 mr-2" />
            Edit Category
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setShowMerchantDialog(true)}>
            <Store className="h-4 w-4 mr-2" />
            Edit Merchant Name
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleToggleBusiness}>
            <Briefcase className="h-4 w-4 mr-2" />
            {transaction.is_business ? "Unmark as Business" : "Mark as Business"}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleToggleIncome}>
            <TrendingUp className="h-4 w-4 mr-2" />
            {transaction.is_income ? "Unmark as Income" : "Mark as Income"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setShowDeleteDialog(true)}
            className="text-red-600 focus:text-red-600"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Transaction
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Edit Category Dialog */}
      <Dialog open={showCategoryDialog} onOpenChange={setShowCategoryDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
            <DialogDescription>
              Select a category for this transaction.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="text-sm text-muted-foreground mb-3 truncate">
              {transaction.merchant || transaction.description}
            </div>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger>
                <SelectValue placeholder="Select a category" />
              </SelectTrigger>
              <SelectContent>
                {categories?.map((cat: { id: string; name: string }) => (
                  <SelectItem key={cat.id} value={cat.id}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCategoryDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSetCategory}
              disabled={!selectedCategory || setCategory.isPending}
            >
              {setCategory.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Merchant Name Dialog */}
      <Dialog open={showMerchantDialog} onOpenChange={setShowMerchantDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Merchant Name</DialogTitle>
            <DialogDescription>
              Set a custom display name for this merchant.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div className="text-sm text-muted-foreground truncate">
              Original: {transaction.description}
            </div>
            <div className="space-y-2">
              <Label htmlFor="merchant-name">Merchant Name</Label>
              <Input
                id="merchant-name"
                value={merchantName}
                onChange={(e) => setMerchantName(e.target.value)}
                placeholder="e.g., Amazon, Starbucks"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMerchantDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSetMerchant}
              disabled={updateTransaction.isPending}
            >
              {updateTransaction.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Delete Transaction
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this transaction? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="p-3 bg-muted rounded-lg">
              <div className="font-medium">
                {transaction.merchant || transaction.description}
              </div>
              <div className="text-sm text-muted-foreground">
                {transaction.category || "Uncategorized"}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteTransaction.isPending}
            >
              {deleteTransaction.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
