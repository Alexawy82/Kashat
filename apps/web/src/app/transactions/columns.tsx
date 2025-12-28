"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ArrowUpDown, Sparkles,
  TrendingUp, Briefcase, CheckCircle2, Repeat
} from "lucide-react"
import { TransactionActions } from "./TransactionActions"

// Enhanced transaction type matching backend
export type Transaction = {
  id: string
  date: string
  amount: number
  merchant?: string
  description?: string
  category?: string
  category_id?: string
  account_id?: string
  is_business?: boolean
  is_income?: boolean
  ai_confidence?: number
  confidence?: "high" | "medium" | "low" | null
  status?: "pending" | "posted"
  is_recurring?: boolean
}

const confidenceColors = {
  high: "bg-green-100 text-green-800 border-green-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-red-100 text-red-800 border-red-200",
}

export const columns: ColumnDef<Transaction>[] = [
  {
    accessorKey: "date",
    header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            className="px-2"
          >
            Date
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        )
    },
    cell: ({ row }) => {
        const date = new Date(row.getValue("date"))
        return (
          <div className="pl-2">
            <div className="font-medium">{date.toLocaleDateString()}</div>
            <div className="text-xs text-muted-foreground">
              {date.toLocaleDateString('en-US', { weekday: 'short' })}
            </div>
          </div>
        )
    },
  },
  {
    accessorKey: "merchant",
    header: "Merchant",
    cell: ({ row }) => {
      const merchant = row.getValue("merchant") as string
      const description = row.original.description
      const hasAI = row.original.ai_confidence !== undefined && row.original.ai_confidence > 0

      return (
        <div className="max-w-[200px]">
          <div className="font-medium truncate flex items-center gap-1">
            {merchant}
            {hasAI && <Sparkles className="h-3 w-3 text-purple-500" />}
          </div>
          {description && description !== merchant && (
            <div className="text-xs text-muted-foreground truncate">
              {description}
            </div>
          )}
        </div>
      )
    }
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => {
        const category = row.getValue("category") as string
        const confidence = row.original.confidence
        const isUncategorized = category === 'Uncategorized' || !category

        return (
            <div className="flex items-center gap-2">
                {isUncategorized ? (
                  <Badge variant="outline" className="text-muted-foreground">
                    Uncategorized
                  </Badge>
                ) : (
                  <>
                    <span className="text-sm">{category}</span>
                    {confidence && (
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-1.5 py-0 h-4 ${confidenceColors[confidence]}`}
                      >
                        {confidence === 'high' && <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />}
                        {confidence}
                      </Badge>
                    )}
                  </>
                )}
            </div>
        )
    }
  },
  {
    accessorKey: "amount",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="px-2 w-full justify-end"
      >
        Amount
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const amount = parseFloat(row.getValue("amount"))
      const formatted = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(Math.abs(amount))

      return (
        <div className={`text-right font-medium ${amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
          {amount < 0 ? '-' : '+'}{formatted}
        </div>
      )
    },
  },
  {
    id: "flags",
    header: "Flags",
    cell: ({ row }) => {
      const isBusiness = row.original.is_business
      const isIncome = row.original.is_income
      const isRecurring = row.original.is_recurring

      if (!isBusiness && !isIncome && !isRecurring) return null

      return (
        <div className="flex items-center gap-1">
          {isRecurring && (
            <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 bg-indigo-50 text-indigo-700 border-indigo-200">
              <Repeat className="h-2.5 w-2.5 mr-0.5" />
              Recurring
            </Badge>
          )}
          {isBusiness && (
            <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 bg-blue-50 text-blue-700 border-blue-200">
              <Briefcase className="h-2.5 w-2.5 mr-0.5" />
              Biz
            </Badge>
          )}
          {isIncome && (
            <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 bg-green-50 text-green-700 border-green-200">
              <TrendingUp className="h-2.5 w-2.5 mr-0.5" />
              Income
            </Badge>
          )}
        </div>
      )
    }
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const transaction = row.original
      return (
        <TransactionActions
          transaction={{
            id: transaction.id,
            merchant: transaction.merchant,
            description: transaction.description,
            category: transaction.category,
            category_id: transaction.category_id,
            is_business: transaction.is_business,
          }}
        />
      )
    },
  },
]
