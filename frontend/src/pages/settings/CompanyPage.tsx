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

export default function CompanyPage() {
  const { data: tenant, isLoading } = useQuery({ queryKey: ['tenant'], queryFn: tenantApi.current })
  return (
    <Page width="narrow">
      <PageHeader title="Empresa" description="Información y plan de tu empresa" />
      <PlanCard />
      {isLoading || !tenant ? <Card padded><SkeletonText lines={6} /></Card> : <CompanyForm tenant={tenant} />}
    </Page>
  )
}
