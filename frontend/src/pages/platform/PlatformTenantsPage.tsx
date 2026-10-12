import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building, Plus } from 'lucide-react'
import { platformApi, VERTICAL_LABEL, type PlatformTenant } from '@/api/platform'
import InvitationLink from '@/components/platform/InvitationLink'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import StatusMark from '@/components/ui/StatusMark'
import { formatDate, formatDateTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { SUBSCRIPTION_STATUS, TENANT_STATUS } from '@/lib/status'
import { useDebounced } from '@/lib/useDebounced'

function OnboardForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient()
  const plans = useQuery({ queryKey: ['platform', 'plans'], queryFn: platformApi.plans })
  const [form, setForm] = useState({ name: '', owner_email: '', vertical: 'bakery', plan: 'business', city: '', tax_id: '' })
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const create = useMutation({
    mutationFn: () => platformApi.onboard(form),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['platform'] }),
  })
  if (create.data) {
    return (
      <div className="space-y-4">
        <Alert tone="success">Empresa creada: {create.data.tenant.name}. La suscripción arranca en prueba.</Alert>
        <InvitationLink url={create.data.invitation_url} />
        <div className="flex justify-end"><Button onClick={onDone}>Listo</Button></div>
      </div>
    )
  }
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); create.mutate() }}>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Nombre comercial" required value={form.name} onChange={set('name')} />
        <Input label="Email del dueño" type="email" required value={form.owner_email} onChange={set('owner_email')} />
        <Select label="Tipo de negocio" value={form.vertical} onChange={set('vertical')}>
          <option value="bakery">{VERTICAL_LABEL.bakery}</option><option value="generic">{VERTICAL_LABEL.generic}</option>
        </Select>
        <Select label="Plan" value={form.plan} onChange={set('plan')}>
          {plans.data?.filter((p) => p.is_active).map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
        </Select>
        <Input label="Ciudad" value={form.city} onChange={set('city')} />
        <Input label="NIT" value={form.tax_id} onChange={set('tax_id')} />
      </div>
      {create.isError && <Alert tone="danger">{getErrorMessage(create.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={create.isPending}>Crear empresa e invitar</Button>
      </div>
    </form>
  )
}

export default function PlatformTenantsPage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [subscription, setSubscription] = useState('')
  const [vertical, setVertical] = useState('')
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(false)
  const search = useDebounced(q, 300)
  const params = { q: search || undefined, status: status || undefined, subscription: subscription || undefined,
                   vertical: vertical || undefined, page }
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['platform', 'tenants', params], queryFn: () => platformApi.tenants(params), placeholderData: (p) => p,
  })
  const columns: Column<PlatformTenant>[] = [
    { key: 'name', header: 'Empresa', primary: true, cell: (t) => (
      <div className="min-w-0"><p className="font-medium text-ink truncate">{t.name}</p>
        <p className="text-xs text-ink-muted truncate">{VERTICAL_LABEL[t.vertical]}{t.city && ` · ${t.city}`}</p></div>
    ) },
    { key: 'plan', header: 'Plan', cell: (t) => t.plan?.name ?? '—' },
    { key: 'sub', header: 'Suscripción', cell: (t) => t.subscription_status ? (
      <span><StatusMark status={SUBSCRIPTION_STATUS[t.subscription_status]} />
        {t.subscription_status === 'trialing' && t.trial_ends_at &&
          <span className="block text-xs text-ink-muted">hasta {formatDate(t.trial_ends_at)}</span>}</span>
    ) : '—' },
    { key: 'members', header: 'Personas', align: 'right', hideOnMobile: true, cell: (t) => t.members ?? 0 },
    { key: 'activity', header: 'Última actividad', hideOnMobile: true, cell: (t) => {
      const last = [t.last_activity, t.last_sale].filter(Boolean).sort().at(-1)
      return <span className="text-ink-muted">{last ? formatDateTime(last) : 'Sin actividad'}</span>
    } },
    { key: 'status', header: 'Estado', cell: (t) => <StatusMark status={TENANT_STATUS[t.status]} /> },
  ]
  return (
    <Page>
      <PageHeader title="Empresas" description="Clientes de GestorPro y Miga"
                  actions={<Button icon={<Plus size={15} />} onClick={() => setCreating(true)}>Nueva empresa</Button>} />
      <div className="grid gap-3 sm:grid-cols-[1fr_170px_170px_170px]">
        <SearchInput label="Buscar empresas" placeholder="Nombre, NIT o email de un usuario" value={q} onChange={(v) => { setQ(v); setPage(1) }} />
        <Select aria-label="Estado" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">Todos los estados</option><option value="active">Activas</option><option value="suspended">Suspendidas</option>
        </Select>
        <Select aria-label="Suscripción" value={subscription} onChange={(e) => { setSubscription(e.target.value); setPage(1) }}>
          <option value="">Toda suscripción</option>
          {Object.entries(SUBSCRIPTION_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </Select>
        <Select aria-label="Tipo de negocio" value={vertical} onChange={(e) => { setVertical(e.target.value); setPage(1) }}>
          <option value="">Todo tipo</option><option value="bakery">Panaderías</option><option value="generic">General</option>
        </Select>
      </div>
      <DataTable caption="Empresas" columns={columns} rows={data?.results} rowKey={(t) => t.id} isLoading={isLoading}
        onRowClick={(t) => navigate(`/platform/tenants/${t.id}`)}
        pagination={{ data, onPageChange: setPage, noun: 'empresas', isFetching }}
        empty={<EmptyState icon={<Building size={20} />} title="Sin empresas con esos filtros" />} />
      <Modal title="Nueva empresa" isOpen={creating} onClose={() => setCreating(false)} size="lg">
        {creating && <OnboardForm onDone={() => setCreating(false)} />}
      </Modal>
    </Page>
  )
}
