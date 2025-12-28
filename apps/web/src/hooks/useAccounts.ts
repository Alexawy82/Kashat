import { useQuery } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

export interface Account {
  id: string
  name: string
  type: string
  last4: string
  currency: string
  transaction_count: number
  first_tx_date: string
  last_tx_date: string
}

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: async (): Promise<Account[]> => {
      const { data, error } = await client.get('/api/accounts')
      if (error) throw new Error('Failed to fetch accounts')
      return (data as Account[]) || []
    },
  })
}
