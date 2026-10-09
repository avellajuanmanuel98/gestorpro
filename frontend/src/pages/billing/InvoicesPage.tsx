import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Plus } from 'lucide-react'
import { billingApi } from '@/api/billing'
import InvoiceDetail from '@/components/billing/InvoiceDetail'
import InvoiceForm from '@/components/billing/InvoiceForm'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import SearchInput from '@/components/ui/SearchInput'
import Select from '@/components/ui/Select'
import { formatDate } from '@/lib/dates'
import { formatCOP } from '@/lib/money'
import { INVOICE_STATUS } from '@/lib/status'
import { useCan } from '@/store/authStore'
import type { Invoice } from '@/types'

export default function InvoicesPage() {
  const can = useCan()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(false)
  const [viewing, setViewing] = useState<number | null>(null)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['invoices', search, status, type, page],
    queryFn: () => billingApi.list({ search: search || undefined, status: status || undefined, invoice_type: type || undefined, page }),
    placeholderData: (prev) => prev,
  })

  const columns: Column<Invoice>[] = [
    { key: 'number', header: 'Número', primary: true, cell: (i) => (
      <div><p className="font-medium text-ink">{i.number}</p>{i.invoice_type === 'quote' && <p className="text-xs text-ink-muted">Cotización</p>}</div>
    ) },
    { key: 'customer', header: 'Cliente', cell: (i) => <span className="truncate">{i.customer_name}</span> },
    { key: 'issue', header: 'Emisión', hideOnMobile: true, cell: (i) => <span className="text-ink-muted">{formatDate(i.issue_date)}</span> },
    { key: 'due', header: 'Vence', cell: (i) => <span className="text-ink-muted">{formatDate(i.due_date)}</span> },
    { key: 'total', header: 'Total', align: 'right', cell: (i) => <span className="font-medium">{formatCOP(i.total)}</span> },
    { key: 'status', header: 'Estado', cell: (i) => <Badge variant={INVOICE_STATUS[i.status].variant}>{INVOICE_STATUS[i.status].label}</Badge> },
  ]
  const filtered = Boolean(search || status || type)

  return (
    <Page>
      <PageHeader title="Facturación" description="Facturas a crédito y cotizaciones"
                  actions={can('billing.create') && <Button icon={<Plus size={15} />} onClick={() => setCreating(true)}>Nuevo documento</Button>} />

      <div className="flex flex-col sm:flex-row gap-3">
        <SearchInput label="Buscar documentos" placeholder="Número o cliente" value={search} onChange={(v) => { setSearch(v); setPage(1) }} />
        <div className="grid grid-cols-2 gap-3 sm:w-[26rem]">
          <Select aria-label="Tipo" value={type} onChange={(e) => { setType(e.target.value); setPage(1) }}>
            <option value="">Todos los tipos</option><option value="invoice">Facturas</option><option value="quote">Cotizaciones</option>
          </Select>
          <Select aria-label="Estado" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
            <option value="">Todos los estados</option>
            {Object.entries(INVOICE_STATUS).map(([value, s]) => <option key={value} value={value}>{s.label}</option>)}
          </Select>
        </div>
      </div>

      <DataTable caption="Documentos" columns={columns} rows={data?.results} rowKey={(i) => i.id} isLoading={isLoading}
        onRowClick={(i) => setViewing(i.id)}
        pagination={{ data, onPageChange: setPage, noun: 'documentos', isFetching }}
        empty={filtered
          ? <EmptyState icon={<FileText size={20} />} title="Sin resultados" description="Ningún documento coincide con los filtros." />
          : <EmptyState icon={<FileText size={20} />} title="Aún no hay documentos"
                        description="Crea facturas a crédito o cotizaciones para clientes empresariales."
                        action={can('billing.create') ? { label: 'Crear documento', onClick: () => setCreating(true), icon: <Plus size={14} /> } : undefined} />}
      />

      <Modal title="Nuevo documento" isOpen={creating} onClose={() => setCreating(false)} size="xl">
        {creating && <InvoiceForm onSuccess={() => setCreating(false)} onCancel={() => setCreating(false)} />}
      </Modal>
      <Modal title="Detalle del documento" isOpen={viewing !== null} onClose={() => setViewing(null)} size="lg">
        {viewing !== null && <InvoiceDetail id={viewing} onClose={() => setViewing(null)} />}
      </Modal>
    </Page>
  )
}
