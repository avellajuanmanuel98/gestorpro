import Alert from './Alert'
import Button from './Button'
import Modal from './Modal'

interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  /** Qué pasará exactamente, con el nombre del objeto afectado */
  description: React.ReactNode
  confirmLabel: string
  tone?: 'danger' | 'primary'
  loading?: boolean
  error?: string | null
  onConfirm: () => void
  onClose: () => void
}

/** Confirmación accesible para acciones destructivas o difíciles de revertir. */
export default function ConfirmDialog({
  isOpen, title, description, confirmLabel, tone = 'danger', loading = false, error, onConfirm, onClose,
}: ConfirmDialogProps) {
  return (
    <Modal title={title} isOpen={isOpen} onClose={onClose} size="sm">
      <div className="space-y-5">
        <div className="text-sm text-ink-muted leading-relaxed">{description}</div>
        {error && <Alert>{error}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={loading}>Cancelar</Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
        </div>
      </div>
    </Modal>
  )
}
