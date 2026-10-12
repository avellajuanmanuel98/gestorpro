import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { tenantApi } from '@/api/auth'
import Alert from '@/components/ui/Alert'
import { Card, CardHeader } from '@/components/ui/Card'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { SkeletonText } from '@/components/ui/Skeleton'
import { formatDate } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore, useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { Tenant } from '@/types'
import StatusMark from '@/components/ui/StatusMark'
import { ACTIVE_STATUS } from '@/lib/status'
import { cn } from '@/lib/cn'
import { Factory, Flame } from 'lucide-react'

type EditableFields = Pick<Tenant, 'name' | 'legal_name' | 'tax_id' | 'email' | 'phone' | 'city' | 'address'>

function PlanCard() {
  const { data: plan, isLoading } = useQuery({ queryKey: ['tenant-plan'], queryFn: tenantApi.plan })
  return (
    <Card>
      <CardHeader title="Plan" description="Lo administra GestorPro. Escríbenos para cambiarlo."
                  actions={plan?.plan.status === 'trialing'
                    ? <StatusMark status={{ label: `En prueba hasta el ${formatDate(plan.plan.trial_ends_at)}`, tone: 'accent', glyph: 'half' }} />
                    : plan?.plan.status === 'active' ? <StatusMark status={ACTIVE_STATUS.active} /> : null} />
      <div className="px-5 pb-5">
        {isLoading || !plan ? <SkeletonText lines={3} /> : (
          <>
            <p className="text-lg font-semibold text-ink mb-4">{plan.plan.name ?? 'Sin plan'}</p>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
              {plan.limits.map((l) => {
                const pct = l.limit ? Math.min(100, Math.round((l.used / l.limit) * 100)) : 0
                return (
                  <div key={l.key}>
                    <dt className="text-xs text-ink-muted">{l.label}</dt>
                    <dd className="text-sm font-medium text-ink num">{l.used} {l.limit === null ? '· ilimitado' : `de ${l.limit}`}</dd>
                    {l.limit !== null && l.limit > 0 && (
                      <div className="mt-1.5 h-1.5 rounded-full bg-surface-muted overflow-hidden" aria-hidden>
                        <div className={`h-full rounded-full ${pct >= 100 ? 'bg-warning' : 'bg-primary'}`} style={{ width: `${pct}%` }} />
                      </div>
                    )}
                  </div>
                )
              })}
            </dl>
          </>
        )}
      </div>
    </Card>
  )
}

function CompanyForm({ tenant }: { tenant: Tenant }) {
  const queryClient = useQueryClient()
  const canEdit = useCan()('tenant.manage')
  const refreshSession = useAuthStore((s) => s.refreshSession)
  const [form, setForm] = useState<EditableFields>({
    name: tenant.name, legal_name: tenant.legal_name, tax_id: tenant.tax_id, email: tenant.email,
    phone: tenant.phone, city: tenant.city, address: tenant.address,
  })
  const set = (key: keyof EditableFields) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const mutation = useMutation({
    mutationFn: () => tenantApi.update(form),
    onSuccess: (updated) => {
      queryClient.setQueryData(['tenant'], updated)
      void refreshSession() // el nombre aparece en la navegación
      toast.success('Datos de la empresa guardados')
    },
  })

  return (
    <Card>
      <CardHeader title="Datos de la empresa" description="Aparecen en tus documentos" />
      <form className="px-5 pb-5 space-y-4" onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}>
        {!canEdit && <Alert tone="info">Solo los administradores pueden editar estos datos.</Alert>}
        <fieldset disabled={!canEdit} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Input label="Nombre comercial" required value={form.name} onChange={set('name')} />
            <Input label="Razón social" value={form.legal_name} onChange={set('legal_name')} />
            <Input label="NIT" value={form.tax_id} onChange={set('tax_id')} placeholder="900123456-7" />
            <Input label="Ciudad" value={form.city} onChange={set('city')} />
            <Input label="Email de contacto" type="email" value={form.email} onChange={set('email')} />
            <Input label="Teléfono" type="tel" value={form.phone} onChange={set('phone')} />
          </div>
          <Input label="Dirección" value={form.address} onChange={set('address')} />
        </fieldset>
        {canEdit && <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null}
                                 submitting={mutation.isPending} submitLabel="Guardar cambios" />}
      </form>
    </Card>
  )
}

const MODULES = [
  { key: 'production', icon: Factory, title: 'Producción y recetas',
    text: 'Para negocios que fabrican o preparan lo que venden: recetas con costo, lotes de producción y descuento automático de insumos.' },
  { key: 'waste', icon: Flame, title: 'Mermas',
    text: 'Registrar lo que se pierde (vencido, dañado, sobrante) y ver cuánto cuesta.' },
]

/** Módulos opcionales: una lavandería no produce; una panadería sí. El servidor también los exige. */
function ModulesCard({ tenant }: { tenant: Tenant }) {
  const queryClient = useQueryClient()
  const canEdit = useCan()('tenant.manage')
  const refreshSession = useAuthStore((s) => s.refreshSession)
  const mutation = useMutation({
    mutationFn: (modules: string[]) => tenantApi.update({ modules }),
    onSuccess: async (updated, modules) => {
      queryClient.setQueryData(['tenant'], updated)
      await refreshSession() // el menú cambia de inmediato
      toast.success(modules.length > (tenant.modules?.length ?? 0) ? 'Módulo activado' : 'Módulo desactivado')
    },
  })
  const active = new Set(tenant.modules ?? [])
  const toggle = (key: string) => {
    const next = new Set(active)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    mutation.mutate([...next].sort())
  }
  return (
    <Card>
      <CardHeader title="Módulos de tu negocio" description="Activa solo lo que usas: el menú se adapta. Los datos de un módulo apagado se conservan." />
      <ul className="divide-y divide-line border-t border-line">
        {MODULES.map(({ key, icon: Icon, title, text }) => {
          const on = active.has(key)
          return (
            <li key={key} className="flex items-start gap-3 px-5 py-4">
              <span className={cn('w-9 h-9 rounded-lg flex items-center justify-center shrink-0',
                on ? 'bg-primary-soft text-primary-ink' : 'bg-surface-muted text-ink-subtle')}><Icon size={17} /></span>
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-medium text-ink">{title}</span>
                <span className="block text-xs text-ink-muted mt-0.5">{text}</span>
              </span>
              <button type="button" role="switch" aria-checked={on} aria-label={title}
                      disabled={!canEdit || mutation.isPending} onClick={() => toggle(key)}
                      className={cn('relative mt-1 h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50',
                        on ? 'bg-primary' : 'bg-line-strong')}>
                <span className={cn('absolute top-0.5 h-5 w-5 rounded-full bg-surface shadow transition-all', on ? 'left-[22px]' : 'left-0.5')} />
              </button>
            </li>
          )
        })}
      </ul>
      {!canEdit && <p className="px-5 pb-4 text-xs text-ink-muted">Solo los administradores pueden cambiar los módulos.</p>}
      {mutation.isError && <div className="px-5 pb-4"><Alert tone="danger">{getErrorMessage(mutation.error)}</Alert></div>}
    </Card>
  )
}

export default function CompanyPage() {
  const { data: tenant, isLoading } = useQuery({ queryKey: ['tenant'], queryFn: tenantApi.current })
  return (
    <Page width="narrow">
      <PageHeader title="Empresa" description="Información, plan y módulos de tu empresa" />
      <PlanCard />
      {isLoading || !tenant ? <Card padded><SkeletonText lines={6} /></Card> : <CompanyForm tenant={tenant} />}
      {tenant && <ModulesCard tenant={tenant} />}
    </Page>
  )
}
