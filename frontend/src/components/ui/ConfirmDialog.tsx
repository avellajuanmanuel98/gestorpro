import Modal from './Modal'
import Button from './Button'

interface ConfirmDialogProps {
  isOpen:        boolean
  title:         string
  /** Qué pasará exactamente, con el nombre del objeto afectado */
  description:   React.ReactNode
  confirmLabel:  string
  tone?:         'danger' | 'primary'
  loading?:      boolean
  error?:        string | null
  onConfirm:     () => void
  onClose:       () => void
}

/** Confirmación accesible para acciones destructivas o difíciles de revertir. */
export default function ConfirmDialog({
  isOpen, title, description, confirmLabel, tone = 'danger', loading = false, error, onConfirm, onClose,
}: ConfirmDialogProps) {
  return (
    <Modal title={title} isOpen={isOpen} onClose={onClose} size="sm">
      <div className="space-y-5">
        <div className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">{description}</div>
        {error && (
          <p role="alert" className="text-sm text-red-700 bg-red-50 dark:bg-red-950/40 dark:text-red-300 px-3 py-2 rounded-lg">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={loading}>Cancelar</Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
