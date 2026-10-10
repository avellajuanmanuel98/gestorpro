import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, History, Lock, Plus } from 'lucide-react'
import { cashApi, type CashSession, type CashSessionDetail } from '@/api/pos'
import OpenSessionCard from '@/components/pos/OpenSessionCard'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import KpiTile from '@/components/ui/KpiTile'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { Skeleton, SkeletonText } from '@/components/ui/Skeleton'
import StatusMark from '@/components/ui/StatusMark'
import Tabs from '@/components/ui/Tabs'
import Textarea from '@/components/ui/Textarea'
import { cn } from '@/lib/cn'
import { formatDateTime, formatTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { DENOMINATIONS, fromCents, toCents } from '@/lib/pos'
import { SESSION_STATUS } from '@/lib/status'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'

const parseAmount = (v: string) => v.replace(/\./g, '').replace(',', '.')
type MovementType = 'income' | 'expense' | 'withdrawal'
const MOVEMENT_COPY: Record<MovementType, { title: string; hint: string; placeholder: string }> = {
  income: { title: 'Registrar ingreso', hint: 'Dinero que entra al cajón sin ser una venta.', placeholder: 'Ej.: base adicional' },
  expense: { title: 'Registrar gasto', hint: 'Pagos hechos con el efectivo de la caja.', placeholder: 'Ej.: compra de huevos' },
  withdrawal: { title: 'Registrar retiro', hint: 'Efectivo que se saca del cajón (consignación, caja fuerte).', placeholder: 'Ej.: consignación al banco' },
}

function Difference({ value }: { value: string | null }) {
  if (value === null) return <span className="text-ink-subtle">—</span>
  const n = Number(value)
  return (
    <span className={cn('num font-medium', n === 0 ? 'text-success' : 'text-warning')}>
      {n === 0 ? 'Cuadró' : `${n > 0 ? '+' : '−'}${formatCOP(Math.abs(n))}`}
    </span>
  )
}

function MovementForm({ session, type, onDone }: { session: CashSessionDetail; type: MovementType; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const save = useMutation({
    mutationFn: () => cashApi.addMovement(session.id, { type, amount: parseAmount(amount), reason }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['cash-current'] })
      toast.success('Movimiento registrado')
      onDone()
    },
  })
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <p className="text-sm text-ink-muted">{MOVEMENT_COPY[type].hint}</p>
      <Input label="Valor" required autoFocus inputMode="numeric" value={amount} onChange={(e) => setAmount(e.target.value)} />
      <Input label="Motivo" required placeholder={MOVEMENT_COPY[type].placeholder} value={reason} onChange={(e) => setReason(e.target.value)} />
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={save.isPending} disabled={!amount || !reason.trim()}>Guardar</Button>
      </div>
    </form>
  )
}

function CloseForm({ session, onDone }: { session: CashSessionDetail; onDone: () => void }) {
  const queryClient = useQueryClient()
  const canManage = useCan()('cash.manage')
  const [counts, setCounts] = useState<Record<number, string>>({})
  const [note, setNote] = useState('')
  const counted = DENOMINATIONS.reduce((sum, d) => sum + d * (Number(counts[d]) || 0), 0)
  const expected = toCents(session.summary.expected)
  const diff = counted * 100 - expected
  const overTolerance = Math.abs(diff) > toCents(session.summary.tolerance)

  const close = useMutation({
    mutationFn: () => cashApi.close(session.id, {
      counted_amount: String(counted),
      denominations: Object.fromEntries(DENOMINATIONS.filter((d) => Number(counts[d]) > 0).map((d) => [String(d), Number(counts[d])])),
      note,
    }),
    onSuccess: (closed) => {
      void queryClient.invalidateQueries({ queryKey: ['cash-current'] })
      void queryClient.invalidateQueries({ queryKey: ['cash-sessions'] })
      void queryClient.invalidateQueries({ queryKey: ['cash-registers'] })
      toast.success(Number(closed.difference) === 0 ? 'Caja cerrada: cuadró perfecto' : 'Caja cerrada con diferencia registrada')
      onDone()
    },
  })

  return (
    <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); close.mutate() }}>
      <div>
        <p className="text-sm font-medium text-ink mb-2">Cuenta el efectivo del cajón</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {DENOMINATIONS.map((d) => (
            <label key={d} className="flex items-center gap-2 rounded-lg border border-line px-3 py-2">
              <span className="w-20 text-sm text-ink num">{formatCOP(d)}</span>
              <span className="text-ink-subtle text-xs">×</span>
              <input inputMode="numeric" aria-label={`Cantidad de ${formatCOP(d)}`} value={counts[d] ?? ''} placeholder="0"
                     onChange={(e) => setCounts((c) => ({ ...c, [d]: e.target.value.replace(/\D/g, '') }))}
                     className="w-full h-8 bg-transparent text-right text-sm num text-ink focus:outline-none" />
            </label>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Contado</p><p className="text-lg font-semibold num text-ink">{formatCOP(counted)}</p></div>
        <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Esperado</p><p className="text-lg font-semibold num text-ink">{formatCOP(session.summary.expected)}</p></div>
        <div className={cn('rounded-xl py-3', diff === 0 ? 'bg-success-soft' : 'bg-warning-soft')}>
          <p className="text-xs text-ink-muted">Diferencia</p><p className="text-lg font-semibold"><Difference value={fromCents(diff)} /></p>
        </div>
      </div>
      {diff !== 0 && (
        <Textarea label="¿Qué pasó? (obligatorio si hay diferencia)" required rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                  placeholder="Ej.: se pagó un domicilio con efectivo de la caja" />
      )}
      {overTolerance && !canManage && (
        <Alert tone="warning">La diferencia supera {formatCOP(session.summary.tolerance)}. Debe cerrar la caja un supervisor.</Alert>
      )}
      {close.isError && <Alert tone="danger">{getErrorMessage(close.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" icon={<Lock size={15} />} loading={close.isPending}
                disabled={(diff !== 0 && !note.trim()) || (overTolerance && !canManage)}>Cerrar caja</Button>
      </div>
    </form>
  )
}

function SessionSummary({ session, live }: { session: CashSessionDetail; live: boolean }) {
  const s = session.summary
  const outflows = Number(s.expenses) + Number(s.withdrawals) + Number(s.voids)
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <KpiTile label="Base inicial" value={formatCOP(s.opening)} />
        <KpiTile label="Ventas en efectivo" value={formatCOP(s.cash_sales)} hint={`${s.sales_count} ventas · ${formatCOP(s.sales_total)} en total`} />
        <KpiTile label="Ingresos" value={formatCOP(s.income)} />
        <KpiTile label="Salidas" value={formatCOP(Math.abs(outflows))} hint="Gastos, retiros y anulaciones" />
        <KpiTile label={live ? 'Debería haber en caja' : 'Esperado al cierre'} value={formatCOP(s.expected)} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader title="Ventas por medio de pago" description="Tarjeta y transferencias no pasan por el cajón." />
          {!s.by_method.length ? <EmptyState compact title="Aún no hay ventas" /> : (
            <ul className="divide-y divide-line border-t border-line">
              {s.by_method.map((m) => (
                <li key={m.method} className="flex justify-between px-5 py-2.5 text-sm"><span className="text-ink">{m.method}</span>
                  <span className="num font-medium">{formatCOP(m.total)}</span></li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title="Movimientos del cajón" />
          {!session.movements.length ? <EmptyState compact title="Sin movimientos" description="Las ventas en efectivo, ingresos, gastos y retiros aparecerán aquí." /> : (
            <ul className="divide-y divide-line border-t border-line max-h-80 overflow-y-auto">
              {[...session.movements].reverse().map((m) => {
                const positive = Number(m.amount) > 0
                return (
                  <li key={m.id} className="flex items-center gap-3 px-5 py-2.5 text-sm">
                    <span className={cn('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', positive ? 'bg-success-soft text-success' : 'bg-warning-soft text-warning')}>
                      {positive ? <ArrowDownLeft size={14} /> : <ArrowUpRight size={14} />}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-ink truncate">{m.type_label}{m.sale_number && ` ${m.sale_number}`}{m.reason && ` · ${m.reason}`}</span>
                      <span className="block text-xs text-ink-muted">{formatTime(m.created_at)} · {m.created_by_name}</span>
                    </span>
                    <span className={cn('num font-medium', positive ? 'text-ink' : 'text-warning')}>{positive ? '+' : '−'}{formatCOP(Math.abs(Number(m.amount)))}</span>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

function CurrentTab() {
  const session = useQuery({ queryKey: ['cash-current'], queryFn: cashApi.current })
  const [movement, setMovement] = useState<MovementType | null>(null)
  const [closing, setClosing] = useState(false)
  if (session.isLoading) return <Skeleton height={320} />
  if (!session.data) return <OpenSessionCard title="No tienes la caja abierta" />
  const s = session.data
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-sm text-ink-muted"><strong className="text-ink">{s.register_name}</strong> · abierta por {s.opened_by_name} el {formatDateTime(s.opened_at)}</p>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" icon={<Plus size={15} />} onClick={() => setMovement('income')}>Ingreso</Button>
          <Button variant="outline" onClick={() => setMovement('expense')}>Gasto</Button>
          <Button variant="outline" onClick={() => setMovement('withdrawal')}>Retiro</Button>
          <Button icon={<Lock size={15} />} onClick={() => setClosing(true)}>Cerrar caja</Button>
        </div>
      </div>
      <SessionSummary session={s} live />
      <Modal title={movement ? MOVEMENT_COPY[movement].title : ''} isOpen={movement !== null} onClose={() => setMovement(null)} size="sm">
        {movement && <MovementForm session={s} type={movement} onDone={() => setMovement(null)} />}
      </Modal>
      <Modal title="Cerrar caja" subtitle="Cuenta el efectivo y compáralo con lo esperado." isOpen={closing} onClose={() => setClosing(false)} size="lg">
        {closing && <CloseForm session={s} onDone={() => setClosing(false)} />}
      </Modal>
    </div>
  )
}

function SessionDetailModal({ id, onClose }: { id: number; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ['cash-session', id], queryFn: () => cashApi.session(id) })
  return (
    <Modal title={data ? `${data.register_name} · ${formatDateTime(data.opened_at)}` : 'Turno de caja'} isOpen onClose={onClose} size="xl">
      {!data ? <SkeletonText lines={8} /> : (
        <div className="space-y-4">
          {data.status === 'closed' && (
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Esperado</p><p className="font-semibold num">{formatCOP(data.expected_amount)}</p></div>
              <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Contado</p><p className="font-semibold num">{formatCOP(data.counted_amount)}</p></div>
              <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Diferencia</p><p className="font-semibold"><Difference value={data.difference} /></p></div>
            </div>
          )}
          {data.closing_note && <Alert tone="info">Cierre ({data.closed_by_name}): {data.closing_note}</Alert>}
          <SessionSummary session={data} live={data.status === 'open'} />
        </div>
      )}
    </Modal>
  )
}

function HistoryTab() {
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<number | null>(null)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['cash-sessions', page], queryFn: () => cashApi.sessions({ page }), placeholderData: (prev) => prev,
  })
  const columns: Column<CashSession>[] = [
    { key: 'register', header: 'Turno', primary: true, cell: (s) => (
      <div><p className="font-medium text-ink">{s.register_name}</p><p className="text-xs text-ink-muted">{s.opened_by_name} · {formatDateTime(s.opened_at)}</p></div>
    ) },
    { key: 'closed', header: 'Cierre', hideOnMobile: true, cell: (s) => (s.closed_at ? formatDateTime(s.closed_at) : '—') },
    { key: 'expected', header: 'Esperado', align: 'right', hideOnMobile: true, cell: (s) => (s.expected_amount ? formatCOP(s.expected_amount) : '—') },
    { key: 'counted', header: 'Contado', align: 'right', hideOnMobile: true, cell: (s) => (s.counted_amount ? formatCOP(s.counted_amount) : '—') },
    { key: 'difference', header: 'Diferencia', align: 'right', cell: (s) => <Difference value={s.difference} /> },
    { key: 'status', header: 'Estado', cell: (s) => <StatusMark status={SESSION_STATUS[s.status]} /> },
  ]
  return (
    <>
      <DataTable caption="Turnos de caja" columns={columns} rows={data?.results} rowKey={(s) => s.id} isLoading={isLoading}
        onRowClick={(s) => setOpen(s.id)} pagination={{ data, onPageChange: setPage, noun: 'turnos', isFetching }}
        empty={<EmptyState icon={<History size={20} />} title="Sin turnos" description="Los turnos de caja aparecerán aquí." />} />
      {open !== null && <SessionDetailModal id={open} onClose={() => setOpen(null)} />}
    </>
  )
}

export default function CashPage() {
  const canManage = useCan()('cash.manage')
  const [tab, setTab] = useState<'current' | 'history'>('current')
  return (
    <Page>
      <PageHeader title="Caja" description="Turno actual, movimientos del cajón y cierres" />
      <Tabs label="Secciones de caja" value={tab} onChange={setTab}
            tabs={[{ id: 'current', label: 'Mi turno' }, { id: 'history', label: canManage ? 'Historial (todas)' : 'Mis turnos' }]} />
      {tab === 'current' ? <CurrentTab /> : <HistoryTab />}
    </Page>
  )
}
