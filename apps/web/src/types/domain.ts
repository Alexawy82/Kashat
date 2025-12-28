export interface Transaction {
  id: string
  date: string
  amount: number
  description: string
  merchant?: string
  category?: string
  category_id?: string
  account_id?: string
  status: 'pending' | 'posted'
  confidence?: 'high' | 'medium' | 'low'
  ai_confidence?: number
  is_business?: boolean
  is_income?: boolean
  is_adjustment?: boolean
  is_recurring?: boolean
  is_subscription?: boolean
  ai_suggestions?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface TransactionFilter {
  page: number
  limit: number
  search?: string
  sortBy?: string
  sortDir?: 'asc' | 'desc'
  uncategorized?: boolean
  hasAiSuggestions?: boolean
  isBusiness?: boolean
  isIncome?: boolean
  categoryId?: string
  accountId?: string
  startDate?: string
  endDate?: string
}

export interface TransactionStats {
  total: number
  minDate?: string
  maxDate?: string
}
