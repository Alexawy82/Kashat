import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

export interface Account {
  id: string
  name: string
  type: string
  last4: string | null
  currency: string
  account_type: string
  transaction_count: number
  first_tx_date: string | null
  last_tx_date: string | null
  balance: number
}

export interface AccountCreate {
  name: string
  type?: string
  last4?: string
  currency?: string
}

export interface AccountUpdate {
  name?: string
  type?: string
  last4?: string
  currency?: string
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

export function useAccount(accountId: string | null) {
  return useQuery({
    queryKey: ['accounts', accountId],
    queryFn: async (): Promise<Account | null> => {
      if (!accountId) return null
      const { data, error } = await client.get(`/api/accounts/${accountId}`)
      if (error) throw new Error('Failed to fetch account')
      return data as Account
    },
    enabled: !!accountId,
  })
}

export function useCreateAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (account: AccountCreate): Promise<Account> => {
      const { data, error } = await client.post('/api/accounts', {
        body: account
      })
      if (error) throw new Error('Failed to create account')
      return data as Account
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

export function useUpdateAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, ...update }: AccountUpdate & { id: string }): Promise<Account> => {
      const { data, error } = await client.put(`/api/accounts/${id}`, {
        body: update
      })
      if (error) throw new Error('Failed to update account')
      return data as Account
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

export function useDeleteAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, force = false }: { id: string; force?: boolean }): Promise<void> => {
      const { error } = await client.delete(`/api/accounts/${id}`, {
        params: { query: { force } }
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}
