import type { BadgeVariant } from '@/components/ui/Badge'
import type { Invoice } from '@/types'

/** Etiquetas y tonos de estado compartidos (antes duplicados en varias páginas). */
export const INVOICE_STATUS: Record<Invoice['status'], { label: string; variant: BadgeVariant }> = {
  draft: { label: 'Borrador', variant: 'default' },
  sent: { label: 'Enviada', variant: 'info' },
  paid: { label: 'Pagada', variant: 'success' },
  overdue: { label: 'Vencida', variant: 'danger' },
  cancelled: { label: 'Cancelada', variant: 'default' },
}

export const ACTIVE_STATUS: Record<'active' | 'inactive', { label: string; variant: BadgeVariant }> = {
  active: { label: 'Activo', variant: 'success' },
  inactive: { label: 'Inactivo', variant: 'default' },
}
