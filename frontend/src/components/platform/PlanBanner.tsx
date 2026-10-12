import { AlertTriangle } from 'lucide-react'
import { formatDate } from '@/lib/dates'
import { useAuthStore, useCan } from '@/store/authStore'

/**
 * Aviso sobre la suscripción para quien administra la empresa. Es informativo:
 * GestorPro no bloquea el trabajo por una prueba vencida o un pago pendiente
 * (solo una suspensión manual, auditada, cierra el acceso).
 */
export default function PlanBanner() {
  const plan = useAuthStore((s) => s.session?.plan)
  const support = useAuthStore((s) => s.session?.support)
  const canSee = useCan()('tenant.manage')
  if (!plan || !canSee || support) return null
  const expired = plan.status === 'trialing' && plan.trial_ends_at && new Date(plan.trial_ends_at) < new Date()
  const text = expired ? `Tu periodo de prueba terminó el ${formatDate(plan.trial_ends_at)}. Escríbenos para activar tu plan; tus datos siguen intactos.`
    : plan.status === 'past_due' ? 'Hay un pago pendiente de tu suscripción. Escríbenos para ponerte al día.'
    : plan.status === 'canceled' ? 'Tu suscripción está cancelada. Escríbenos si quieres reactivarla.'
    : null
  if (!text) return null
  return (
    <div role="status" className="shrink-0 bg-warning-soft text-ink border-b border-line px-4 py-2 flex items-center gap-2 text-sm">
      <AlertTriangle size={15} className="text-warning shrink-0" aria-hidden />{text}
    </div>
  )
}
