import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { History } from 'lucide-react'
import { platformApi, type PlatformEvent } from '@/api/platform'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import Select from '@/components/ui/Select'
import { formatDateTime } from '@/lib/dates'

const ACTIONS: [string, string][] = [
  ['', 'Todas las acciones'], ['tenant.', 'Empresas (alta, estado, invitaciones)'], ['subscription.', 'Suscripciones'],
  ['plan.', 'Planes'], ['support.', 'Accesos de soporte'],
]

export default function PlatformEventsPage() {
  const [params] = useSearchParams()
  const tenant = params.get('tenant') ?? undefined
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['platform', 'events', tenant, action, page],
    queryFn: () => platformApi.events({ tenant, action: action || undefined, page }), placeholderData: (p) => p,
  })
  const columns: Column<PlatformEvent>[] = [
    { key: 'summary', header: 'Acción', primary: true, cell: (e) => (
      <div><p className="text-ink">{e.summary}</p><p className="text-xs text-ink-muted">{e.actor_label}{e.ip && ` · ${e.ip}`}</p></div>) },
    { key: 'tenant', header: 'Empresa', cell: (e) => e.tenant_name ?? <span className="text-ink-subtle">—</span> },
    { key: 'when', header: 'Fecha', cell: (e) => <span className="text-ink-muted whitespace-nowrap">{formatDateTime(e.created_at)}</span> },
  ]
  return (
    <Page>
      <PageHeader title="Bitácora de la plataforma" description="Todo lo que el equipo de GestorPro hace sobre las empresas. No se puede editar ni borrar." />
      <div className="sm:w-80">
        <Select aria-label="Tipo de acción" value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }}>
          {ACTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
      </div>
      <DataTable caption="Bitácora" columns={columns} rows={data?.results} rowKey={(e) => e.id} isLoading={isLoading}
        pagination={{ data, onPageChange: setPage, noun: 'acciones', isFetching }}
        empty={<EmptyState icon={<History size={20} />} title="Sin acciones registradas" />} />
    </Page>
  )
}
