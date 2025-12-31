'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  CreditCard,
  Home,
  Landmark,
  Shield,
  Tv,
  HelpCircle,
  DollarSign,
} from 'lucide-react'
import { formatAmount } from '@/app/subscriptions/lib/recurringUtils'

interface CategoryData {
  type: string
  count: number
  monthly_total: number
  annual_total: number
}

// API returns by_type as object: {subscription: {count, monthly}, ...}
// We transform it to array format for rendering
type ApiByType = Record<string, { count: number; monthly: number }>

interface CategoryOverviewProps {
  data: ApiByType | null
  totalMonthly?: number
  totalAnnual?: number
  isLoading?: boolean
  onCategoryClick?: (category: string) => void
}

// Keys must match backend API response: subscription, bill, loan, credit_card, insurance, unknown
const categoryConfig: Record<string, { icon: typeof Tv; label: string; color: string; bgColor: string }> = {
  subscription: {
    icon: Tv,
    label: 'Subscriptions',
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
  },
  bill: {
    icon: Home,
    label: 'Bills',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
  },
  loan: {
    icon: Landmark,
    label: 'Loans',
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
  },
  credit_card: {
    icon: CreditCard,
    label: 'Credit Cards',
    color: 'text-green-600',
    bgColor: 'bg-green-100',
  },
  insurance: {
    icon: Shield,
    label: 'Insurance',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
  },
  unknown: {
    icon: HelpCircle,
    label: 'Other',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
  },
}

function CategoryCard({
  category,
  percentage,
  onClick,
}: {
  category: CategoryData
  percentage: number
  onClick?: () => void
}) {
  const config = categoryConfig[category.type] || categoryConfig.unknown
  const Icon = config.icon

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md hover:border-primary/30 ${onClick ? '' : ''}`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className={`p-2 rounded-lg ${config.bgColor}`}>
            <Icon className={`h-4 w-4 ${config.color}`} />
          </div>
          <span className="text-xs text-muted-foreground">{category.count} items</span>
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium truncate">{config.label}</p>
          <p className="text-lg font-semibold">{formatAmount(category.monthly_total)}</p>
          <p className="text-xs text-muted-foreground">/month</p>
        </div>
        <div className="mt-3">
          <Progress value={percentage} className="h-1.5" />
          <p className="text-[10px] text-muted-foreground mt-1">{percentage.toFixed(0)}% of total</p>
        </div>
      </CardContent>
    </Card>
  )
}

export function CategoryOverview({ data, totalMonthly, totalAnnual, isLoading, onCategoryClick }: CategoryOverviewProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-4">
              <div className="h-20 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!data || Object.keys(data).length === 0) {
    return null
  }

  // Transform API object to array format
  const categories: CategoryData[] = Object.entries(data).map(([type, values]) => ({
    type,
    count: values.count,
    monthly_total: values.monthly,
    annual_total: values.monthly * 12,
  }))

  // Calculate totals if not provided
  const calculatedTotalMonthly = totalMonthly ?? categories.reduce((sum, c) => sum + c.monthly_total, 0)
  const calculatedTotalAnnual = totalAnnual ?? calculatedTotalMonthly * 12

  // Sort by monthly total descending
  const sortedCategories = categories.sort((a, b) => b.monthly_total - a.monthly_total)

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <div className="flex items-center justify-between p-4 bg-gradient-to-r from-primary/5 to-primary/10 rounded-lg border">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-full">
            <DollarSign className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total Monthly Recurring</p>
            <p className="text-2xl font-bold">{formatAmount(calculatedTotalMonthly)}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm text-muted-foreground">Annual Projection</p>
          <p className="text-lg font-semibold text-muted-foreground">{formatAmount(calculatedTotalAnnual)}</p>
        </div>
      </div>

      {/* Category Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {sortedCategories.map((category) => {
          const percentage = calculatedTotalMonthly > 0
            ? (category.monthly_total / calculatedTotalMonthly) * 100
            : 0

          return (
            <CategoryCard
              key={category.type}
              category={category}
              percentage={percentage}
              onClick={onCategoryClick ? () => onCategoryClick(category.type) : undefined}
            />
          )
        })}
      </div>
    </div>
  )
}
