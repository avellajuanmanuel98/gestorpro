import Alert from './Alert'
import Button from './Button'

/** Pie estándar de formulario: error del servidor + cancelar/guardar. */
export default function FormActions({ error, submitting, submitLabel, onCancel }: {
  error?: string | null; submitting: boolean; submitLabel: string; onCancel?: () => void
}) {
  return (
    <div className="space-y-4 pt-1">
      {error && <Alert>{error}</Alert>}
      <div className="flex justify-end gap-2">
        {onCancel && <Button variant="ghost" onClick={onCancel} disabled={submitting}>Cancelar</Button>}
        <Button type="submit" loading={submitting}>{submitLabel}</Button>
      </div>
    </div>
  )
}
