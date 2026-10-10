import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Factory, Sparkles } from 'lucide-react'
import { analyticsApi } from '@/api/analytics'
import { productionApi, type Batch } from '@/api/inventory'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import Select from '@/components/ui/Select'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatQty, formatUnitCost } from '@/lib/catalog'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useDebounced } from '@/lib/useDebounced'
import { useAuthStore, useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'

const num = (v: string) => v.replace(',', '.')

function ProduceForm({ initial }: { initial?: { recipe: string; quantity: string } }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const recipes = useQuery({ queryKey: ['recipes', 'all'], queryFn: () => productionApi.recipes({ page_size: 200 }) })
  const producible = recipes.data?.results.filter((r) => !r.consume_on_sale) ?? []
  const [recipeId, setRecipeId] = useState(initial?.recipe ?? '')
  const [quantity, setQuantity] = useState(initial?.quantity ?? '')
  const [actual, setActual] = useState<Record<string, string>>({})
  const recipe = producible.find((r) => String(r.id) === recipeId)
  const qty = useDebounced(num(quantity), 300)
  const plan = useQuery({
    queryKey: ['production-plan', recipeId, qty], queryFn: () => productionApi.plan(Number(recipeId), qty),
    enabled: !!recipeId && Number(qty) > 0,
  })

  const produce = useMutation({
    mutationFn: () => productionApi.produce({
      recipe: Number(recipeId), quantity: num(quantity),
      actual: Object.fromEntries(Object.entries(actual).filter(([, v]) => v !== '').map(([k, v]) => [k, num(v)])),
    }),
    onSuccess: (b) => {
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
      void queryClient.invalidateQueries({ queryKey: ['items'] })
      void queryClient.invalidateQueries({ queryKey: ['pos-catalog'] })
      toast.success(`${b.number}: ${formatQty(b.produced_quantity, b.unit_symbol)} de ${b.product_name} agregados al inventario`)
      setQuantity(''); setActual({})
    },
  })

  if (recipes.isSuccess && !producible.length) {
    return <EmptyState icon={<Factory size={20} />} title="Primero crea una receta"
                       description="La producción usa la receta para saber qué ingredientes descontar."
                       action={{ label: 'Ir a recetas', onClick: () => navigate('/recipes') }} />
  }
  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); produce.mutate() }}>
      <div className="grid sm:grid-cols-[1fr_180px] gap-4">
        <Select label="¿Qué produjiste?" value={recipeId} onChange={(e) => { setRecipeId(e.target.value); setActual({}) }}>
          <option value="">Elige un producto…</option>
          {producible.map((r) => <option key={r.id} value={r.id}>{r.product_name} (rinde {formatQty(r.yield_quantity, r.product_unit)})</option>)}
        </Select>
        <Input label={`Cantidad producida${recipe ? ` (${recipe.product_unit})` : ''}`} inputMode="decimal" value={quantity}
               onChange={(e) => setQuantity(e.target.value)} disabled={!recipe} />
      </div>
      {plan.data && (
        <div className="rounded-xl border border-line overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-muted/60 text-xs text-ink-muted"><tr>
              <th className="text-left px-3 py-2 font-medium">Ingrediente</th><th className="text-right px-3 py-2 font-medium">Según receta</th>
              <th className="text-right px-3 py-2 font-medium w-36">Usado de verdad</th><th className="text-right px-3 py-2 font-medium">Existencia</th></tr></thead>
            <tbody className="divide-y divide-line">
              {plan.data.lines.map((l) => (
                <tr key={l.ingredient}>
                  <td className="px-3 py-2 text-ink">{l.name}</td>
                  <td className="px-3 py-2 text-right num">{formatQty(l.quantity, l.unit_symbol)}</td>
                  <td className="px-3 py-1.5">
                    <input inputMode="decimal" aria-label={`Cantidad usada de ${l.name}`} placeholder={formatQty(l.quantity)}
                           value={actual[l.ingredient] ?? ''} onChange={(e) => setActual((a) => ({ ...a, [l.ingredient]: e.target.value }))}
                           className="w-full h-8 rounded-lg border border-line-strong bg-surface px-2 text-right text-sm num text-ink" />
                  </td>
                  <td className={cn('px-3 py-2 text-right num', l.short ? 'text-warning font-medium' : 'text-ink-muted')}>
                    {l.short && <AlertTriangle size={12} className="inline mr-1" aria-label="No alcanza" />}{formatQty(l.stock, l.unit_symbol)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {plan.data.estimated_cost && (
            <p className="px-3 py-2 text-sm text-ink-muted border-t border-line bg-surface-muted/40">
              Costo estimado {formatCOP(plan.data.estimated_cost)} · {formatUnitCost(plan.data.estimated_unit_cost)} por {recipe?.product_unit}
            </p>
          )}
        </div>
      )}
      {plan.data?.lines.some((l) => l.short) && (
        <Alert tone="warning">Según el sistema, algún ingrediente no alcanza. Puedes registrar igual (quedará en negativo) y corregirlo con una compra o un conteo.</Alert>
      )}
      {produce.isError && <Alert tone="danger">{getErrorMessage(produce.error)}</Alert>}
      <div className="flex justify-end">
        <Button type="submit" size="lg" loading={produce.isPending} disabled={!recipe || !(Number(num(quantity)) > 0)}>Registrar producción</Button>
      </div>
    </form>
  )
}

const WEEKDAY = new Intl.DateTimeFormat('es-CO', { weekday: 'long' })
const DAY = new Intl.DateTimeFormat('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })
const parseISO = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return new Date(y, m - 1, d) }
const isoOf = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** Miga: cuánto producir según lo vendido el mismo día de la semana en las últimas 4 semanas. */
function SuggestionCard({ onProduce, canRegister }: { onProduce: (recipe: number, quantity: string) => void; canRegister: boolean }) {
  const today = new Date()
  const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)
  const [target, setTarget] = useState(isoOf(tomorrow))
  const { data, isLoading } = useQuery({ queryKey: ['production-suggestion', target], queryFn: () => analyticsApi.suggestion(target) })
  const weekday = WEEKDAY.format(parseISO(target))
  const rows = data?.rows.filter((r) => Number(r.average_sold) > 0) ?? []
  const options: [string, string][] = [[isoOf(today), 'Hoy'], [isoOf(tomorrow), 'Mañana']]
  return (
    <Card>
      <CardHeader title="Producción sugerida"
                  description={`Para el ${DAY.format(parseISO(target))}: promedio vendido los ${weekday}s de las últimas 4 semanas, menos lo que ya hay.`}
                  actions={<div role="radiogroup" aria-label="Día" className="inline-flex gap-1 rounded-xl bg-surface-muted p-1">
                    {options.map(([iso, label]) => (
                      <button key={iso} type="button" role="radio" aria-checked={target === iso} onClick={() => setTarget(iso)}
                              className={cn('h-7 px-3 rounded-lg text-sm', target === iso ? 'bg-surface text-ink font-medium shadow-sm' : 'text-ink-muted hover:text-ink')}>
                        {label}
                      </button>
                    ))}
                  </div>} />
      {isLoading ? <div className="px-5 pb-5"><Skeleton height={120} /></div> : !data || data.weeks_with_data < 2 ? (
        <EmptyState compact icon={<Sparkles size={20} />} title="Aún no hay suficiente historia"
                    description={`Se necesitan ventas de al menos 2 ${weekday}s para sugerir cantidades (hay ${data?.weeks_with_data ?? 0}). No inventamos números.`} />
      ) : !rows.length ? (
        <EmptyState compact icon={<Sparkles size={20} />} title={`Sin ventas de productos elaborados los ${weekday}s`} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-ink-muted bg-surface-muted/60"><tr>
              <th className="text-left font-medium py-2 px-5">Producto</th>
              <th className="text-left font-medium py-2 px-3">Últimos {weekday}s</th>
              <th className="text-right font-medium py-2 px-3">Promedio</th>
              <th className="text-right font-medium py-2 px-3">Merma prom.</th>
              <th className="text-right font-medium py-2 px-3">Hay</th>
              <th className="text-right font-medium py-2 px-3">Sugerido</th>
              {canRegister && <th className="py-2 px-5" />}
            </tr></thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.item} className={Number(r.suggested) ? '' : 'text-ink-muted'}>
                  <td className="py-2 px-5 text-ink">{r.name}</td>
                  <td className="py-2 px-3"><span className="inline-flex gap-1">
                    {r.history.map((h, i) => <span key={i} className="min-w-7 px-1 rounded bg-surface-muted text-xs text-center num">{formatQty(h)}</span>)}
                  </span></td>
                  <td className="py-2 px-3 text-right num">{formatQty(r.average_sold, r.unit)}</td>
                  <td className="py-2 px-3 text-right num">{Number(r.average_wasted) ? formatQty(r.average_wasted, r.unit) : '—'}</td>
                  <td className="py-2 px-3 text-right num">{formatQty(r.stock, r.unit)}</td>
                  <td className="py-2 px-3 text-right">
                    <span className="font-semibold text-ink num">{Number(r.suggested) ? formatQty(r.suggested, r.unit) : 'Alcanza'}</span>
                    {r.batches && r.batch_size && <span className="block text-xs text-ink-muted">{r.batches} tanda{r.batches === 1 ? '' : 's'} de {formatQty(r.batch_size)}</span>}
                  </td>
                  {canRegister && (
                    <td className="py-2 px-5 text-right">
                      {r.recipe && Number(r.suggested) > 0 && (
                        <Button size="sm" variant="outline" onClick={() => onProduce(r.recipe!, r.suggested)}>Producir</Button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-5 py-2 text-xs text-ink-muted border-t border-line">Basado en {data.weeks_with_data} {weekday}s con ventas. Es una guía: ajústala si hay un pedido o un festivo.</p>
        </div>
      )}
    </Card>
  )
}

export default function ProductionPage() {
  const can = useCan()
  const isBakery = useAuthStore((s) => s.session?.tenant?.vertical) === 'bakery'
  const [preset, setPreset] = useState<{ key: number; recipe: string; quantity: string } | undefined>()
  const [page, setPage] = useState(1)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['batches', page], queryFn: () => productionApi.batches({ page }), placeholderData: (prev) => prev,
    enabled: can('production.view'),
  })
  const columns: Column<Batch>[] = [
    { key: 'number', header: 'Lote', primary: true, cell: (b) => (
      <div><p className="font-medium text-ink">{b.product_name}</p><p className="text-xs text-ink-muted">{b.number} · {formatDateTime(b.created_at)}</p></div>
    ) },
    { key: 'qty', header: 'Producido', align: 'right', cell: (b) => formatQty(b.produced_quantity, b.unit_symbol) },
    ...(can('catalog.view_costs') ? [
      { key: 'unit', header: 'Costo / unidad', align: 'right' as const, cell: (b: Batch) => formatUnitCost(b.unit_cost) },
      { key: 'total', header: 'Costo total', align: 'right' as const, hideOnMobile: true, cell: (b: Batch) => formatCOP(b.total_cost) },
    ] : []),
    { key: 'by', header: 'Registró', hideOnMobile: true, cell: (b) => <span className="text-ink-muted">{b.created_by_name}</span> },
  ]
  return (
    <Page>
      <PageHeader title="Producción" description="Registra lo que sale del horno: descuenta ingredientes y suma producto"
                  actions={<Link to="/recipes" className="text-sm text-primary-ink hover:underline">Ver recetas</Link>} />
      {can('production.register') && (
        <Card><CardHeader title="Registrar producción" /><div id="produce-form" className="px-5 pb-5">
          <ProduceForm key={preset?.key} initial={preset} />
        </div></Card>
      )}
      {isBakery && can('production.view') && (
        <SuggestionCard canRegister={can('production.register')} onProduce={(recipe, quantity) => {
          setPreset({ key: Date.now(), recipe: String(recipe), quantity })
          document.getElementById('produce-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }} />
      )}
      {can('production.view') && (
        <DataTable caption="Lotes de producción" columns={columns} rows={data?.results} rowKey={(b) => b.id} isLoading={isLoading}
          pagination={{ data, onPageChange: setPage, noun: 'lotes', isFetching }}
          empty={<EmptyState compact icon={<Factory size={20} />} title="Aún no hay producción registrada" />} />
      )}
    </Page>
  )
}
