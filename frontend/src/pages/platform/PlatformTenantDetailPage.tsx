import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Eye, KeyRound, MailPlus, PauseCircle, PlayCircle } from 'lucide-react'
import { platformApi, VERTICAL_LABEL, type PlatformTenantFull } from '@/api/platform'
import InvitationLink from '@/components/platform/InvitationLink'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import Select from '@/components/ui/Select'
import { SkeletonText } from '@/components/ui/Skeleton'
import StatusMark from '@/components/ui/StatusMark'
import Textarea from '@/components/ui/Textarea'
import { formatDate, formatDateTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { SUBSCRIPTION_STATUS, TENANT_STATUS } from '@/lib/status'
import { useAuthStore } from '@/store/authStore'

const MODULE_LABEL: Record<string, string> = { production: 'Producción y recetas', waste: 'Mermas' }
const toDateInput = (iso: string | null) => (iso ? iso.slice(0, 10) : '')
// Fin del día en hora de Colombia: "hasta el 31" incluye el 31 completo
const fromDateInput = (d: string) => (d ? `${d}T23:59:59-05:00` : null)

function SubscriptionForm({ tenant, onDone }: { tenant: PlatformTenantFull; onDone: () => void }) {
  const queryClient = useQueryClient()
  const plans = useQuery({ queryKey: ['platform', 'plans'], queryFn: platformApi.plans })
  const rawStatus = tenant.subscription_status === 'trial_expired' ? 'trialing' : tenant.subscription_status ?? 'trialing'
  const initial = {
    plan: tenant.plan?.code ?? '', status: rawStatus, trial_ends_at: toDateInput(tenant.trial_ends_at),
    current_period_end: toDateInput(tenant.current_period_end), note: '',
  }
  const [form, setForm] = useState(initial)
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))
  const save = useMutation({
    // Solo lo que cambió: así la bitácora no registra cambios que nadie hizo
    mutationFn: () => platformApi.changeSubscription(tenant.id, {
      note: form.note,
      ...(form.plan !== initial.plan && { plan: form.plan }),
      ...(form.status !== initial.status && { status: form.status }),
      ...(form.trial_ends_at !== initial.trial_ends_at && { trial_ends_at: fromDateInput(form.trial_ends_at) }),
      ...(form.current_period_end !== initial.current_period_end && { current_period_end: fromDateInput(form.current_period_end) }),
    }),
    onSuccess: (data) => { queryClient.setQueryData(['platform', 'tenant', tenant.id], data); void queryClient.invalidateQueries({ queryKey: ['platform'] }); onDone() },
  })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <div className="grid sm:grid-cols-2 gap-4">
        <Select label="Plan" value={form.plan} onChange={set('plan')}>
          {plans.data?.filter((p) => p.is_active || p.code === form.plan).map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
        </Select>
        <Select label="Estado" value={form.status} onChange={set('status')}>
          <option value="trialing">En prueba</option><option value="active">Activa</option>
          <option value="past_due">Pago pendiente</option><option value="canceled">Cancelada</option>
        </Select>
        <Input label="Fin de la prueba" type="date" value={form.trial_ends_at} onChange={set('trial_ends_at')} />
        <Input label="Pagado hasta (fin del período)" type="date" value={form.current_period_end} onChange={set('current_period_end')} />
      </div>
      <p className="text-xs text-ink-muted">Fechas vacías = sin vencimiento (por ejemplo, la edición local). Las fechas son informativas: nada se bloquea solo.</p>
      <Textarea label="Nota (queda en la bitácora)" rows={2} value={form.note} onChange={set('note')} placeholder="Ej.: pago de octubre recibido por transferencia" />
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={save.isPending}>Guardar</Button>
      </div>
    </form>
  )
}

function StatusForm({ tenant, onDone }: { tenant: PlatformTenantFull; onDone: () => void }) {
  const queryClient = useQueryClient()
  const suspending = tenant.status === 'active'
  const [reason, setReason] = useState('')
  const save = useMutation({
    mutationFn: () => platformApi.setStatus(tenant.id, { status: suspending ? 'suspended' : 'active', reason }),
    onSuccess: (data) => { queryClient.setQueryData(['platform', 'tenant', tenant.id], data); void queryClient.invalidateQueries({ queryKey: ['platform'] }); onDone() },
  })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <Alert tone={suspending ? 'warning' : 'info'}>
        {suspending
          ? 'Nadie de la empresa podrá entrar mientras esté suspendida. Los datos se conservan y la empresa lo verá en su auditoría al volver.'
          : 'La empresa vuelve a tener acceso de inmediato.'}
      </Alert>
      <Textarea label={suspending ? 'Motivo (obligatorio)' : 'Motivo (opcional)'} rows={2} value={reason}
                onChange={(e) => setReason(e.target.value)} required={suspending} />
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" variant={suspending ? 'danger' : 'primary'} loading={save.isPending}>
          {suspending ? 'Suspender empresa' : 'Reactivar empresa'}</Button>
      </div>
    </form>
  )
}

function ReinviteForm({ tenant, onDone }: { tenant: PlatformTenantFull; onDone: () => void }) {
  const [email, setEmail] = useState(tenant.members.find((m) => m.role === 'Propietario')?.email ?? '')
  const send = useMutation({ mutationFn: () => platformApi.reinvite(tenant.id, email) })
  if (send.data) return <div className="space-y-4"><InvitationLink url={send.data.invitation_url} />
    <div className="flex justify-end"><Button onClick={onDone}>Listo</Button></div></div>
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); send.mutate() }}>
      <p className="text-sm text-ink-muted">Para cuando el dueño perdió el enlace o nunca lo usó. Las invitaciones anteriores a ese email quedan anuladas.</p>
      <Input label="Email del propietario" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      {send.isError && <Alert tone="danger">{getErrorMessage(send.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={send.isPending}>Generar enlace</Button>
      </div>
    </form>
  )
}

function SupportForm({ tenant, onDone }: { tenant: PlatformTenantFull; onDone: () => void }) {
  const enterSupport = useAuthStore((s) => s.enterSupport)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [reason, setReason] = useState('')
  const start = useMutation({
    mutationFn: async () => {
      const grant = await platformApi.startSupport(tenant.id, reason)
      await enterSupport(grant.access)
    },
    onSuccess: () => { queryClient.clear(); onDone(); navigate('/dashboard') },
  })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); start.mutate() }}>
      <Alert tone="info">
        Verás {tenant.name} como la ven ellos, <strong>solo para consultar</strong> y por 30 minutos. No podrás cambiar nada.
        La empresa verá en su auditoría que entraste y por qué.
      </Alert>
      <Textarea label="Motivo (la empresa lo verá)" rows={2} required minLength={10} value={reason}
                onChange={(e) => setReason(e.target.value)} placeholder="Ej.: el dueño reporta que no ve las ventas de ayer" />
      {start.isError && <Alert tone="danger">{getErrorMessage(start.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" icon={<Eye size={15} />} loading={start.isPending} disabled={reason.trim().length < 10}>Entrar en modo soporte</Button>
      </div>
    </form>
  )
}

function ResetLink({ tenant, email }: { tenant: PlatformTenantFull; email: string }) {
  const make = useMutation({ mutationFn: () => platformApi.resetLink(tenant.id, email) })
  if (make.data) {
    return <InvitationLink url={make.data.invitation_url}
                           hint={`Entrégaselo solo a ${email}: con él escribe su contraseña nueva (nadie más la conoce). Sirve una vez y vence en 24 horas. La empresa lo verá en su auditoría.`} />
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-muted">Genera un enlace de un solo uso para que <strong className="text-ink">{email}</strong> cree una contraseña nueva. Úsalo cuando la persona perdió el acceso y la empresa no puede ayudarla (por ejemplo, el dueño).</p>
      {make.isError && <Alert tone="danger">{getErrorMessage(make.error)}</Alert>}
      <div className="flex justify-end"><Button loading={make.isPending} onClick={() => make.mutate()}>Generar enlace</Button></div>
    </div>
  )
}

type Dialog = 'subscription' | 'status' | 'reinvite' | 'support' | null

export default function PlatformTenantDetailPage() {
  const id = Number(useParams().id)
  const [dialog, setDialog] = useState<Dialog>(null)
  const [resetEmail, setResetEmail] = useState<string | null>(null)
  const { data: t, isLoading, isError, error } = useQuery({ queryKey: ['platform', 'tenant', id], queryFn: () => platformApi.tenant(id) })
  const close = () => setDialog(null)
  if (isError) return <Page><Alert tone="danger">{getErrorMessage(error)}</Alert></Page>
  if (isLoading || !t) return <Page><SkeletonText lines={8} /></Page>
  const titles: Record<Exclude<Dialog, null>, string> = {
    subscription: 'Cambiar suscripción', status: t.status === 'active' ? 'Suspender empresa' : 'Reactivar empresa',
    reinvite: 'Invitación de propietario', support: 'Modo soporte',
  }
  return (
    <Page>
      <Link to="/platform/tenants" className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink"><ArrowLeft size={14} /> Empresas</Link>
      <PageHeader title={t.name} description={`${VERTICAL_LABEL[t.vertical]} · creada el ${formatDate(t.created_at)}${t.city ? ` · ${t.city}` : ''}`}
                  actions={<div className="flex flex-wrap gap-2">
                    <Button variant="outline" icon={<MailPlus size={15} />} onClick={() => setDialog('reinvite')}>Invitar propietario</Button>
                    <Button variant="outline" icon={t.status === 'active' ? <PauseCircle size={15} /> : <PlayCircle size={15} />}
                            onClick={() => setDialog('status')}>{t.status === 'active' ? 'Suspender' : 'Reactivar'}</Button>
                    <Button icon={<Eye size={15} />} onClick={() => setDialog('support')} disabled={t.status !== 'active'}>Ver como soporte</Button>
                  </div>} />
      <div className="flex flex-wrap gap-4 text-sm">
        <StatusMark status={TENANT_STATUS[t.status]} />
        {t.subscription_status && <StatusMark status={SUBSCRIPTION_STATUS[t.subscription_status]} />}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Suscripción" actions={<Button size="sm" variant="outline" onClick={() => setDialog('subscription')}>Cambiar</Button>} />
          <dl className="px-5 pb-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div><dt className="text-xs text-ink-muted">Plan</dt><dd className="font-medium text-ink">{t.plan?.name ?? '—'}</dd></div>
            <div><dt className="text-xs text-ink-muted">Estado</dt><dd>{t.subscription_status ? SUBSCRIPTION_STATUS[t.subscription_status].label : '—'}</dd></div>
            <div><dt className="text-xs text-ink-muted">Fin de la prueba</dt><dd className="num">{t.trial_ends_at ? formatDate(t.trial_ends_at) : 'Sin fecha'}</dd></div>
            <div><dt className="text-xs text-ink-muted">Pagado hasta</dt><dd className="num">{t.current_period_end ? formatDate(t.current_period_end) : 'Sin fecha'}</dd></div>
          </dl>
        </Card>
        <Card>
          <CardHeader title="Uso del plan" description={`${t.products} productos activos · ${t.locations} sucursal${t.locations === 1 ? '' : 'es'}`} />
          <ul className="px-5 pb-5 space-y-3">
            {t.usage.map((u) => {
              const pct = u.limit ? Math.min(100, Math.round((u.used / u.limit) * 100)) : 0
              return (
                <li key={u.key}>
                  <div className="flex justify-between text-sm"><span className="text-ink">{u.label}</span>
                    <span className="num text-ink-muted">{u.used} {u.limit === null ? '· ilimitado' : `de ${u.limit}`}</span></div>
                  {u.limit !== null && <div className="mt-1 h-1.5 rounded-full bg-surface-muted overflow-hidden" aria-hidden>
                    <div className={`h-full rounded-full ${pct >= 100 ? 'bg-warning' : 'bg-primary'}`} style={{ width: `${pct}%` }} /></div>}
                </li>
              )
            })}
            <li className="text-xs text-ink-muted pt-1">
              Módulos: {t.modules.length ? t.modules.map((m) => MODULE_LABEL[m] ?? m).join(', ') : 'ninguno opcional'}
            </li>
          </ul>
        </Card>
      </div>

      <Card>
        <CardHeader title="Personas con acceso" description="Solo datos de cuenta: la plataforma no ve clientes, ventas ni facturas de la empresa." />
        {!t.members.length ? <EmptyState compact title="Nadie ha aceptado la invitación todavía" /> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead className="text-xs text-ink-muted bg-surface-muted/60"><tr>
              <th className="text-left font-medium py-2 px-5">Persona</th><th className="text-left font-medium py-2 px-3">Rol</th>
              <th className="text-left font-medium py-2 px-3">Estado</th><th className="text-left font-medium py-2 px-5">Último ingreso</th>
              <th className="py-2 px-5"><span className="sr-only">Acciones</span></th></tr></thead>
            <tbody className="divide-y divide-line">
              {t.members.map((m) => (
                <tr key={m.email}><td className="py-2 px-5"><span className="block text-ink">{m.name || m.email}</span>
                  {m.name && <span className="text-xs text-ink-muted">{m.email}</span>}</td>
                  <td className="py-2 px-3">{m.role}</td><td className="py-2 px-3 text-ink-muted">{m.status === 'active' ? 'Activo' : m.status}</td>
                  <td className="py-2 px-5 text-ink-muted">{m.last_login ? formatDateTime(m.last_login) : 'Nunca'}</td>
                  <td className="py-2 px-5 text-right"><Button size="xs" variant="ghost" icon={<KeyRound size={13} />} onClick={() => setResetEmail(m.email)}>Contraseña</Button></td></tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Accesos de soporte" />
          {!t.support_sessions.length ? <EmptyState compact title="Nadie de soporte ha entrado" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {t.support_sessions.map((s) => (
                <li key={s.id} className="px-5 py-2.5 text-sm">
                  <p className="text-ink">{s.agent} · {formatDateTime(s.started_at)}</p>
                  <p className="text-xs text-ink-muted">{s.reason} · {s.requests} consultas{s.ended_at ? '' : ' · abierta'}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title="Bitácora" actions={<Link to={`/platform/events?tenant=${t.id}`} className="text-xs font-medium text-primary-ink hover:underline">Ver todo</Link>} />
          {!t.events.length ? <EmptyState compact title="Sin acciones de la plataforma" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {t.events.map((e) => (
                <li key={e.id} className="px-5 py-2.5 text-sm"><p className="text-ink">{e.summary}</p>
                  <p className="text-xs text-ink-muted">{e.actor} · {formatDateTime(e.created_at)}</p></li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Modal title="Contraseña nueva" isOpen={resetEmail !== null} onClose={() => setResetEmail(null)} size="md">
        {resetEmail && <ResetLink tenant={t} email={resetEmail} />}
      </Modal>
      <Modal title={dialog ? titles[dialog] : ''} isOpen={dialog !== null} onClose={close} size="md">
        {dialog === 'subscription' && <SubscriptionForm tenant={t} onDone={close} />}
        {dialog === 'status' && <StatusForm tenant={t} onDone={close} />}
        {dialog === 'reinvite' && <ReinviteForm tenant={t} onDone={close} />}
        {dialog === 'support' && <SupportForm tenant={t} onDone={close} />}
      </Modal>
    </Page>
  )
}
