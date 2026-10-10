import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Minus, Plus, Printer, Search, ShoppingBasket, Trash2, Wallet } from 'lucide-react'
import { customersApi } from '@/api/customers'
import { cashApi, salesApi, type POSItem, type Sale } from '@/api/pos'
import OpenSessionCard from '@/components/pos/OpenSessionCard'
import PaymentModal from '@/components/pos/PaymentModal'
import Receipt from '@/components/pos/Receipt'
import Button from '@/components/ui/Button'
import Combobox from '@/components/ui/Combobox'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatQty } from '@/lib/catalog'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/dates'
import { formatCOP } from '@/lib/money'
import { cartTotals, fromCents, isWholeUnit, lineTotals, stepQuantity } from '@/lib/pos'
import { useCan } from '@/store/authStore'
import { useCartStore } from '@/store/cartStore'

const normalize = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

async function searchCustomers(term: string) {
  const res = await customersApi.list({ search: term || undefined, status: 'active', page_size: 15 })
  return res.results.map((c) => ({ id: c.id, label: c.company_name || c.full_name, description: c.document_number || undefined }))
}

function ProductGrid({ onAdd }: { onAdd: (item: POSItem) => void }) {
  const catalog = useQuery({ queryKey: ['pos-catalog'], queryFn: salesApi.catalog, staleTime: 60_000 })
  const [category, setCategory] = useState<number | 'all'>('all')
  const [term, setTerm] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)

  // F2 enfoca la búsqueda (también sirve para el lector de código de barras)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'F2') { e.preventDefault(); searchRef.current?.focus() } }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const items = useMemo(() => {
    const all = catalog.data?.items ?? []
    const q = normalize(term.trim())
    return all.filter((i) => (category === 'all' || i.category === category)
      && (!q || normalize(i.name).includes(q) || normalize(i.code).includes(q)))
  }, [catalog.data, category, term])

  const addFromSearch = () => {
    const q = normalize(term.trim())
    const exact = catalog.data?.items.find((i) => normalize(i.code) === q)
    const pick = exact ?? (items.length === 1 ? items[0] : undefined)
    if (pick) { onAdd(pick); setTerm('') }
  }

  return (
    <div className="flex flex-col min-h-0 h-full">
      <div className="space-y-3 pb-3">
        <div className="relative">
          <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-subtle pointer-events-none" />
          <input ref={searchRef} value={term} onChange={(e) => setTerm(e.target.value)} autoFocus
                 onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addFromSearch() } }}
                 aria-label="Buscar producto" placeholder="Buscar producto o código  (F2)"
                 className="w-full h-12 pl-10 pr-3 rounded-xl border border-line-strong bg-surface text-[15px] text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-[var(--focus)]" />
        </div>
        <div role="tablist" aria-label="Categorías" className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          {[{ id: 'all' as const, name: 'Todo' }, ...(catalog.data?.categories ?? [])].map((c) => (
            <button key={c.id} type="button" role="tab" aria-selected={category === c.id} onClick={() => setCategory(c.id)}
                    className={cn('shrink-0 h-10 px-4 rounded-full text-sm font-medium transition-colors',
                      category === c.id ? 'bg-ink text-canvas' : 'bg-surface border border-line text-ink-muted hover:text-ink')}>
              {c.name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto -mx-1 px-1 pb-2">
        {catalog.isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={96} />)}
          </div>
        ) : !items.length ? (
          <EmptyState compact title={term ? 'Sin coincidencias' : 'No hay productos para vender'}
                      description={term ? 'Prueba con otro nombre o código.' : 'Crea productos activos en el catálogo.'} />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
            {items.map((item) => {
              const out = item.tracks_stock && Number(item.stock) <= 0
              return (
                <button key={item.id} type="button" onClick={() => onAdd(item)}
                        className="group text-left min-h-24 rounded-2xl border border-line bg-surface p-3.5 flex flex-col justify-between
                                   hover:border-primary hover:shadow-overlay active:scale-[0.98] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus)]">
                  <span className="text-sm font-medium text-ink leading-snug line-clamp-2">{item.name}</span>
                  <span className="mt-2 flex items-end justify-between gap-2">
                    <span className="text-base font-semibold text-ink num">{formatCOP(item.price_with_tax)}
                      {item.unit !== 'und' && <span className="text-xs font-normal text-ink-subtle"> /{item.unit_symbol}</span>}</span>
                    {item.tracks_stock && (
                      <span className={cn('text-[11px] num', out ? 'text-warning' : 'text-ink-subtle')}>
                        {out ? 'Sin registro' : formatQty(item.stock, item.unit_symbol)}
                      </span>
                    )}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function Cart({ sessionLabel, onCharge }: { sessionLabel: string; onCharge: () => void }) {
  const { lines, customer, setQuantity, remove, setCustomer, clear } = useCartStore()
  const totals = cartTotals(lines)
  const count = lines.reduce((n, l) => n + (isWholeUnit(l.unit) ? Number(l.quantity) : 1), 0)

  return (
    <div className="flex flex-col h-full min-h-0 bg-surface border border-line rounded-2xl">
      <div className="px-4 pt-4 pb-3 border-b border-line space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Venta actual</h2>
          <Link to="/cash" className="text-xs text-ink-muted hover:text-ink inline-flex items-center gap-1"><Wallet size={13} />{sessionLabel}</Link>
        </div>
        <Combobox label="Cliente" value={customer} onChange={setCustomer} search={searchCustomers} queryKey="pos-customers"
                  placeholder="Consumidor final" />
      </div>

      <div className="flex-1 overflow-y-auto">
        {!lines.length ? (
          <EmptyState compact icon={<ShoppingBasket size={20} />} title="Toca un producto para agregarlo"
                      description="Con el buscador y Enter también puedes agregar por código." />
        ) : (
          <ul className="divide-y divide-line">
            {lines.map((line) => (
              <li key={line.itemId} className="px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-ink leading-snug">{line.name}</p>
                  <p className="text-sm font-semibold text-ink num">{formatCOP(fromCents(lineTotals(line).total))}</p>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <button type="button" aria-label={`Quitar uno de ${line.name}`} onClick={() => setQuantity(line.itemId, stepQuantity(line, -1))}
                          className="w-10 h-10 rounded-xl border border-line-strong flex items-center justify-center text-ink hover:bg-surface-muted"><Minus size={16} /></button>
                  <input aria-label={`Cantidad de ${line.name}`} inputMode="decimal" value={line.quantity}
                         onChange={(e) => setQuantity(line.itemId, e.target.value.replace(',', '.'))}
                         className="w-16 h-10 rounded-xl border border-line-strong bg-surface text-center text-sm num text-ink" />
                  <button type="button" aria-label={`Agregar uno de ${line.name}`} onClick={() => setQuantity(line.itemId, stepQuantity(line, 1))}
                          className="w-10 h-10 rounded-xl border border-line-strong flex items-center justify-center text-ink hover:bg-surface-muted"><Plus size={16} /></button>
                  <span className="text-xs text-ink-subtle">{line.unitSymbol}</span>
                  <button type="button" aria-label={`Eliminar ${line.name}`} onClick={() => remove(line.itemId)}
                          className="ml-auto w-10 h-10 rounded-xl flex items-center justify-center text-ink-subtle hover:text-danger hover:bg-danger-soft"><Trash2 size={16} /></button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-line p-4 space-y-3">
        <div className="space-y-1 text-sm">
          <p className="flex justify-between text-ink-muted"><span>Subtotal</span><span className="num">{formatCOP(fromCents(totals.subtotal))}</span></p>
          {totals.tax > 0 && <p className="flex justify-between text-ink-muted"><span>IVA</span><span className="num">{formatCOP(fromCents(totals.tax))}</span></p>}
          <p className="flex justify-between items-baseline pt-1"><span className="text-ink font-medium">Total</span>
            <span className="text-2xl font-semibold text-ink num">{formatCOP(fromCents(totals.total))}</span></p>
        </div>
        <Button size="lg" fullWidth className="h-14 text-lg" disabled={!lines.length || lines.some((l) => !(Number(l.quantity) > 0))}
                onClick={onCharge}>
          Cobrar{count > 0 && ` · ${count} ${count === 1 ? 'producto' : 'productos'}`}
        </Button>
        {lines.length > 0 && (
          <button type="button" onClick={clear} className="w-full text-sm text-ink-muted hover:text-danger">Vaciar venta</button>
        )}
      </div>
    </div>
  )
}

function SaleDone({ sale, onNext }: { sale: Sale; onNext: () => void }) {
  return (
    <Modal title="Venta registrada" isOpen onClose={onNext} size="md">
      <div className="space-y-5">
        <div className="text-center space-y-1">
          <CheckCircle2 size={36} className="mx-auto text-success" />
          <p className="text-sm text-ink-muted">{sale.number} · {formatDateTime(sale.created_at)}</p>
          {Number(sale.change_given) > 0 ? (
            <>
              <p className="text-sm text-ink-muted pt-2">Cambio a entregar</p>
              <p className="text-4xl font-semibold text-ink num">{formatCOP(sale.change_given)}</p>
            </>
          ) : <p className="text-2xl font-semibold text-ink num pt-2">{formatCOP(sale.total)}</p>}
        </div>
        <div className="max-h-64 overflow-y-auto rounded-xl border border-line bg-white"><Receipt sale={sale} /></div>
        <div className="grid grid-cols-2 gap-3">
          <Button variant="outline" size="lg" icon={<Printer size={16} />} onClick={() => window.print()}>Imprimir ticket</Button>
          <Button size="lg" autoFocus onClick={onNext}>Nueva venta</Button>
        </div>
      </div>
    </Modal>
  )
}

export default function PosPage() {
  const queryClient = useQueryClient()
  const can = useCan()
  const session = useQuery({ queryKey: ['cash-current'], queryFn: cashApi.current })
  const methods = useQuery({ queryKey: ['payment-methods'], queryFn: salesApi.paymentMethods, staleTime: 300_000 })
  const { lines, customer, add, clear } = useCartStore()
  const [charging, setCharging] = useState(false)
  const [done, setDone] = useState<Sale | null>(null)

  if (session.isLoading) return <div className="p-8"><Skeleton height={400} /></div>
  if (!session.data) return <div className="px-4"><OpenSessionCard /></div>

  const s = session.data
  return (
    <div className="h-[calc(100dvh-3.5rem)] xl:h-dvh p-3 md:p-5 grid gap-4 grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_380px] grid-rows-[minmax(0,1fr)_minmax(0,1fr)] lg:grid-rows-1">
      <ProductGrid onAdd={(item) => add(item)} />
      <Cart sessionLabel={`${s.register_name} · ${s.opened_by_name}`} onCharge={() => setCharging(true)} />
      {charging && methods.data && (
        <PaymentModal lines={lines} customerId={customer?.id ?? null} methods={methods.data}
                      canDiscount={can('sales.discount')} onClose={() => setCharging(false)}
                      onPaid={(sale) => {
                        setCharging(false); setDone(sale); clear()
                        void queryClient.invalidateQueries({ queryKey: ['pos-catalog'] })
                        void queryClient.invalidateQueries({ queryKey: ['cash-current'] })
                        void queryClient.invalidateQueries({ queryKey: ['sales'] })
                        void queryClient.invalidateQueries({ queryKey: ['sales-today'] })
                      }} />
      )}
      {done && <SaleDone sale={done} onNext={() => setDone(null)} />}
    </div>
  )
}
