import { UseMutationResult } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { toast } from '@/components/ui/Toaster'

interface ToastOptions {
  loading?: string
  success?: string | ((data: unknown) => string)
  error?: string | ((error: Error) => string)
}

/**
 * Hook that shows toast notifications for mutation states.
 * Use this to provide consistent feedback across all mutations.
 *
 * @example
 * const deleteMutation = useDeleteTransaction()
 * useMutationToast(deleteMutation, {
 *   loading: 'Deleting transaction...',
 *   success: 'Transaction deleted',
 *   error: 'Failed to delete transaction'
 * })
 */
export function useMutationToast<TData, TError extends Error, TVariables>(
  mutation: UseMutationResult<TData, TError, TVariables>,
  options: ToastOptions
) {
  const toastId = useRef<string | number | undefined>(undefined)

  useEffect(() => {
    if (mutation.isPending && options.loading) {
      toastId.current = toast.loading(options.loading)
    }

    if (mutation.isSuccess && options.success) {
      if (toastId.current) {
        toast.dismiss(toastId.current)
      }
      const message = typeof options.success === 'function'
        ? options.success(mutation.data)
        : options.success
      toast.success(message)
      toastId.current = undefined
    }

    if (mutation.isError && options.error) {
      if (toastId.current) {
        toast.dismiss(toastId.current)
      }
      const message = typeof options.error === 'function'
        ? options.error(mutation.error)
        : options.error
      toast.error(message)
      toastId.current = undefined
    }
  }, [mutation.isPending, mutation.isSuccess, mutation.isError, mutation.data, mutation.error, options])
}

/**
 * Wraps a mutation with automatic toast notifications.
 * Returns the original mutation with toast side effects.
 */
export function withMutationToast<TData, TError extends Error, TVariables>(
  mutation: UseMutationResult<TData, TError, TVariables>,
  options: ToastOptions
): UseMutationResult<TData, TError, TVariables> {
  useMutationToast(mutation, options)
  return mutation
}
