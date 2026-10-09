import type { LifecycleSpec, StatusSpec } from '@/components/ui/StatusMark'
import type { Invoice, Member } from '@/types'

/** Estados compartidos. La forma del símbolo comunica el estado; el color lo refuerza. */
export const INVOICE_STATUS: Record<Invoice['status'], LifecycleSpec> = {
  draft: { label: 'Borrador', tone: 'neutral', step: 1 },
  sent: { label: 'Enviada', tone: 'info', step: 2 },
  paid: { label: 'Pagada', tone: 'success', step: 3 },
  overdue: { label: 'Vencida', tone: 'danger', step: 2, stalled: true },
  cancelled: { label: 'Cancelada', tone: 'neutral', step: 1, voided: true },
}

export const ACTIVE_STATUS: Record<'active' | 'inactive', StatusSpec> = {
  active: { label: 'Activo', tone: 'success', glyph: 'solid' },
  inactive: { label: 'Inactivo', tone: 'neutral', glyph: 'hollow' },
}

export const MEMBER_STATUS: Record<Member['status'], StatusSpec> = {
  active: { label: 'Activo', tone: 'success', glyph: 'solid' },
  invited: { label: 'Invitado', tone: 'info', glyph: 'half' },
  suspended: { label: 'Suspendido', tone: 'warning', glyph: 'paused' },
}
