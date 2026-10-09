import { Pencil, Trash2 } from 'lucide-react'

/** Acciones de fila: siempre visibles (no solo al pasar el ratón) y con nombre accesible. */
export default function RowActions({ name, onEdit, onDelete }: { name: string; onEdit?: () => void; onDelete?: () => void }) {
  const btn = 'p-1.5 rounded-lg text-ink-subtle transition-colors'
  return (
    <div className="flex items-center justify-end gap-0.5">
      {onEdit && (
        <button type="button" onClick={onEdit} aria-label={`Editar ${name}`} title="Editar"
                className={`${btn} hover:text-ink hover:bg-surface-muted`}><Pencil size={15} /></button>
      )}
      {onDelete && (
        <button type="button" onClick={onDelete} aria-label={`Eliminar ${name}`} title="Eliminar"
                className={`${btn} hover:text-danger hover:bg-danger-soft`}><Trash2 size={15} /></button>
      )}
    </div>
  )
}
