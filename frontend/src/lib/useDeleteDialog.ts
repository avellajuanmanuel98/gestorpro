import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { getErrorMessage } from './errors'
import { toast } from '@/store/toastStore'

/** Estado + mutación para el diálogo de confirmación de borrado de una lista. */
export function useDeleteDialog<T>(remove: (item: T) => Promise<void>, invalidate: string, successMessage: (item: T) => string) {
  const queryClient = useQueryClient()
  const [target, setTarget] = useState<T | null>(null)
  const mutation = useMutation({
    mutationFn: () => remove(target as T),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [invalidate] })
      toast.success(successMessage(target as T))
      setTarget(null)
    },
  })
  return {
    target,
    open: (item: T) => { mutation.reset(); setTarget(item) },
    close: () => setTarget(null),
    confirm: () => mutation.mutate(),
    loading: mutation.isPending,
    error: mutation.isError ? getErrorMessage(mutation.error) : null,
  }
}
