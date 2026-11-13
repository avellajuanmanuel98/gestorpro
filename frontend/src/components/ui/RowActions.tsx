import { Pencil, Trash2 } from 'lucide-react'
import { useDisplayStore } from '@/store/displayStore'

/**
 * Acciones de fila: siempre visibles (no solo al pasar el ratón) y con nombre accesible.
 * En modo fácil se escriben con palabras, no solo con un ícono.
 */
export default function RowActions({ name, onEdit, onDelete }: { name: string; onEdit?: () => void; onDelete?: () => void }) {
  const easy = useDisplayStore((s) => s.easyMode)
  const btn = easy
    ? 'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium transition-colors'
    : 'p-1.5 rounded-lg text-ink-subtle transition-colors'
  return (
    <div className="flex items-center justify-end gap-1">
      {onEdit && (
        <button type="button" onClick={onEdit} aria-label={`Editar ${name}`} title="Editar"
                className={`${btn} ${easy ? 'text-primary-ink hover:bg-primary-soft' : 'hover:text-ink hover:bg-surface-muted'}`}>
          <Pencil size={15} />{easy && 'Editar'}
        </button>
      )}
      {onDelete && (
        <button type="button" onClick={onDelete} aria-label={`Eliminar ${name}`} title="Eliminar"
                className={`${btn} ${easy ? 'text-danger hover:bg-danger-soft' : 'hover:text-danger hover:bg-danger-soft'}`}>
          <Trash2 size={15} />{easy && 'Eliminar'}
        </button>
      )}
    </div>
  )
}
