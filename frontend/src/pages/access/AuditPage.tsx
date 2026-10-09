import { Fragment, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, History } from 'lucide-react'
import { auditApi } from '@/api/access'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import Pagination from '@/components/ui/Pagination'
import Select from '@/components/ui/Select'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { formatDateTime } from '@/lib/dates'
import type { AuditEntry } from '@/types'

const CATEGORIES = [
  { value: '', label: 'Todas las acciones' },
  { value: 'auth.', label: 'Sesiones' },
  { value: 'access.', label: 'Usuarios y roles' },
  { value: 'catalog.', label: 'Catálogo y precios' },
  { value: 'billing.', label: 'Facturación' },
  { value: 'customers.', label: 'Clientes' },
  { value: 'suppliers.', label: 'Proveedores' },
  { value: 'hr.', label: 'Personal' },
  { value: 'tenancy.', label: 'Empresa' },
]

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  return String(value)
}

function Changes({ entry }: { entry: AuditEntry }) {
  const rows = Object.entries(entry.changes)
  if (!rows.length) return <p className="text-xs text-ink-muted">Sin detalle de campos.</p>
  return (
    <table className="text-xs w-full max-w-3xl">
      <thead>
        <tr className="text-left text-ink-muted">
          <th className="py-1 pr-4 font-medium">Campo</th><th className="py-1 pr-4 font-medium">Antes</th>
          <th className="py-1 font-medium">Después</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([field, [before, after]]) => (
          <tr key={field} className="align-top">
            <td className="py-1 pr-4 font-mono text-ink-muted">{field}</td>
            <td className="py-1 pr-4 text-ink-muted line-through decoration-line-strong break-all">{formatValue(before)}</td>
            <td className="py-1 text-ink break-all">{formatValue(after)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function AuditPage() {
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['audit', page, action, dateFrom, dateTo],
    queryFn: () => auditApi.list({ page, action: action || undefined, date_from: dateFrom || undefined,
                                   date_to: dateTo || undefined }),
    placeholderData: (prev) => prev,
  })

  const onFilter = (fn: () => void) => { fn(); setPage(1) }

  return (
    <Page>
      <PageHeader title="Auditoría"
                  description="Registro inalterable de quién hizo qué y cuándo en tu empresa." />

      <div className="grid gap-3 sm:grid-cols-[220px_170px_170px]">
        <Select aria-label="Tipo de acción" value={action} onChange={(e) => onFilter(() => setAction(e.target.value))}>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </Select>
        <Input type="date" aria-label="Desde" value={dateFrom} onChange={(e) => onFilter(() => setDateFrom(e.target.value))} />
        <Input type="date" aria-label="Hasta" value={dateTo} onChange={(e) => onFilter(() => setDateTo(e.target.value))} />
      </div>

      <section className="bg-surface border border-line rounded-2xl overflow-hidden">
        {isLoading ? <SkeletonTable rows={8} /> : !data?.results.length ? (
          <EmptyState icon={<History size={24} />} title="Sin registros"
                      description="No hay acciones que coincidan con los filtros." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-muted/60 border-b border-line">
                <tr className="text-left text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
                  <th className="px-6 py-3 w-8" /><th className="px-2 py-3">Fecha</th>
                  <th className="px-6 py-3">Usuario</th><th className="px-6 py-3">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.results.map((entry) => {
                  const open = expanded === entry.id
                  return (
                    <Fragment key={entry.id}>
                      <tr className="hover:bg-surface-muted/60 cursor-pointer"
                          onClick={() => setExpanded(open ? null : entry.id)}>
                        <td className="pl-6 py-3 text-ink-subtle">
                          <button aria-expanded={open} aria-label="Ver detalle" className="align-middle">
                            {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                          </button>
                        </td>
                        <td className="px-2 py-3 whitespace-nowrap tabular-nums text-ink-muted">
                          {formatDateTime(entry.created_at)}
                        </td>
                        <td className="px-6 py-3 text-ink">{entry.actor_label}</td>
                        <td className="px-6 py-3">
                          <p className="text-ink">{entry.summary}</p>
                          <p className="text-[11px] font-mono text-ink-subtle">{entry.action}</p>
                        </td>
                      </tr>
                      {open && (
                        <tr className="bg-surface-muted/40">
                          <td />
                          <td colSpan={3} className="px-2 py-3 space-y-2">
                            <Changes entry={entry} />
                            {entry.ip && <p className="text-[11px] text-ink-subtle">IP {entry.ip}</p>}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <Pagination data={data} onPageChange={setPage} noun="registros" isFetching={isFetching} />
      </section>
    </Page>
  )
}
