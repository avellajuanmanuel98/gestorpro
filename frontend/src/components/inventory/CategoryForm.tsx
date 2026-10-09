import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { catalogApi } from '@/api/catalog'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import { getErrorMessage } from '@/lib/errors'
import { toast } from '@/store/toastStore'
import type { Category, CategoryKind } from '@/types'

export default function CategoryForm({ kind, category, onSuccess, onCancel }: {
  kind: CategoryKind; category?: Category; onSuccess: () => void; onCancel?: () => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(category?.name ?? '')
  const [description, setDescription] = useState(category?.description ?? '')
  const mutation = useMutation({
    mutationFn: () => category
      ? catalogApi.updateCategory(category.id, { name, description })
      : catalogApi.createCategory({ name, description, kind }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast.success(category ? 'Categoría actualizada' : `Categoría «${name}» creada`)
      onSuccess()
    },
  })
  return (
    <form onSubmit={(e) => { e.preventDefault(); mutation.mutate() }} className="space-y-4">
      <Input label="Nombre" required autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder={kind === 'ingredient' ? 'Harinas' : 'Panes rellenos'} />
      <Textarea label="Descripción" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={category ? 'Guardar' : 'Crear categoría'} onCancel={onCancel} />
    </form>
  )
}
