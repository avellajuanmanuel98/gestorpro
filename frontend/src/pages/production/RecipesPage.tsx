import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChefHat, Plus, Trash2 } from 'lucide-react'
import { catalogApi } from '@/api/catalog'
import { productionApi, type Recipe } from '@/api/inventory'
import ItemPicker, { type ItemOption } from '@/components/inventory/ItemPicker'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import DataTable, { type Column } from '@/components/ui/DataTable'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import SearchInput from '@/components/ui/SearchInput'
import { SkeletonText } from '@/components/ui/Skeleton'
import Textarea from '@/components/ui/Textarea'
import { compatibleUnits, convertQty, formatQty, formatUnitCost, previewMargin } from '@/lib/catalog'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { Unit } from '@/types'

interface Line { key: number; item: ItemOption | null; quantity: string; unit: string; waste: string }
let nextKey = 1
const num = (v: string) => v.replace(',', '.')
const fromRecipe = (r: Recipe): Line[] => r.lines.map((l) => ({
  key: nextKey++, quantity: l.quantity.replace(/\.?0+$/, ''), unit: l.unit, waste: String(Number(l.waste_pct) || ''),
  // Lo mínimo que el formulario necesita del ingrediente: su unidad (para convertir) y su costo
  item: { id: l.ingredient, label: l.ingredient_name,
          item: { id: l.ingredient, name: l.ingredient_name, unit: l.ingredient_unit_code, avg_cost: l.ingredient_avg_cost } } as unknown as ItemOption,
}))

/** Costo estimado mientras se escribe (vista previa; el oficial lo calcula el servidor al guardar). */
function previewCost(lines: Line[], units: Unit[]): { total: number; complete: boolean } {
  let total = 0, complete = true
  for (const l of lines) {
    if (!l.item) continue
    const cost = Number(l.item.item.avg_cost ?? 0)
    const qty = convertQty(Number(num(l.quantity)) || 0, l.unit || l.item.item.unit, l.item.item.unit, units)
    if (!cost) complete = false
    total += (qty || 0) * (1 + (Number(num(l.waste)) || 0) / 100) * cost
  }
  return { total, complete }
}

function RecipeForm({ recipe, onDone }: { recipe?: Recipe; onDone: () => void }) {
  const queryClient = useQueryClient()
  const canSeeCosts = useCan()('catalog.view_costs')
  const units = useQuery({ queryKey: ['units'], queryFn: catalogApi.units, staleTime: Infinity })
  const [product, setProduct] = useState<ItemOption | null>(recipe
    ? ({ id: recipe.product, label: recipe.product_name, item: { price: recipe.product_price, unit_symbol: recipe.product_unit } } as unknown as ItemOption)
    : null)
  const [yieldQty, setYieldQty] = useState(recipe ? recipe.yield_quantity.replace(/\.?0+$/, '') : '')
  const [notes, setNotes] = useState(recipe?.notes ?? '')
  const [lines, setLines] = useState<Line[]>(recipe ? fromRecipe(recipe)
    : [{ key: nextKey++, item: null, quantity: '', unit: '', waste: '' }])
  const set = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))
  const preview = units.data ? previewCost(lines, units.data) : { total: 0, complete: false }
  const unitCost = Number(num(yieldQty)) > 0 ? preview.total / Number(num(yieldQty)) : 0
  const margin = product ? previewMargin(String(product.item.price ?? 0), String(unitCost)) : null

  const save = useMutation({
    mutationFn: () => productionApi.saveRecipe({
      product: product!.id, yield_quantity: num(yieldQty), notes,
      lines: lines.filter((l) => l.item).map((l) => ({ ingredient: l.item!.id, quantity: num(l.quantity),
                                                       unit: l.unit || l.item!.item.unit, waste_pct: num(l.waste) || '0' })),
    }),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ['recipes'] })
      toast.success(recipe && r.version !== recipe.version ? `Se creó la versión ${r.version} (la anterior ya se usó en producción)` : 'Receta guardada')
      onDone()
    },
  })
  const ready = product && Number(num(yieldQty)) > 0 && lines.some((l) => l.item) && lines.every((l) => !l.item || Number(num(l.quantity)) > 0)

  return (
    <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); if (ready) save.mutate() }}>
      <div className="grid sm:grid-cols-[1fr_200px] gap-4">
        {recipe ? <Input label="Producto" value={recipe.product_name} readOnly /> : (
          <ItemPicker label="Producto" required value={product} onChange={setProduct} queryKey="recipe-products"
                      params={{ kind: 'finished_good' }} placeholder="Pan de bono, almojábana…" />
        )}
        <Input label={`Rinde (${product?.item.unit_symbol ?? 'und'})`} required inputMode="decimal" value={yieldQty}
               onChange={(e) => setYieldQty(e.target.value)} hint="Cuánto sale de esta preparación." />
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium text-ink">Ingredientes</p>
        {lines.map((l) => {
          const options = l.item && units.data ? compatibleUnits(units.data, l.item.item.unit) : []
          return (
            <div key={l.key} className="grid gap-2 sm:grid-cols-[1fr_100px_120px_90px_40px] items-end rounded-xl border border-line p-3">
              <ItemPicker label="Ingrediente" value={l.item} queryKey="recipe-ingredients" params={{}} placeholder="Buscar…"
                          onChange={(item) => set(l.key, { item, unit: item?.item.unit ?? '' })} />
              <Input label="Cantidad" inputMode="decimal" value={l.quantity} onChange={(e) => set(l.key, { quantity: e.target.value })} />
              <label className="space-y-1.5 text-sm">
                <span className="font-medium text-ink">Unidad</span>
                <select value={l.unit} disabled={!l.item} onChange={(e) => set(l.key, { unit: e.target.value })}
                        className="w-full h-9 rounded-lg border border-line-strong bg-surface px-2 text-sm text-ink">
                  {options.map((u) => <option key={u.code} value={u.code}>{u.name}</option>)}
                </select>
              </label>
              <Input label="Desperdicio %" inputMode="decimal" placeholder="0" value={l.waste} onChange={(e) => set(l.key, { waste: e.target.value })} />
              <button type="button" aria-label="Quitar ingrediente" onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))}
                      className="h-9 w-10 rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft flex items-center justify-center"><Trash2 size={15} /></button>
            </div>
          )
        })}
        <Button type="button" variant="outline" size="sm" icon={<Plus size={14} />}
                onClick={() => setLines((ls) => [...ls, { key: nextKey++, item: null, quantity: '', unit: '', waste: '' }])}>Agregar ingrediente</Button>
      </div>

      {canSeeCosts && (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Costo de la preparación</p><p className="font-semibold num">{formatCOP(preview.total)}</p></div>
          <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Costo por unidad</p><p className="font-semibold num">{formatUnitCost(unitCost)}</p></div>
          <div className="rounded-xl bg-surface-muted/70 py-3"><p className="text-xs text-ink-muted">Margen</p><p className="font-semibold num">{margin !== null ? `${margin.toLocaleString('es-CO')} %` : '—'}</p></div>
        </div>
      )}
      {canSeeCosts && !preview.complete && lines.some((l) => l.item) && (
        <Alert tone="warning">Algunos ingredientes no tienen costo todavía: registra una compra para que el costo sea real.</Alert>
      )}
      <Textarea label="Preparación / notas" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={save.isPending} disabled={!ready}>Guardar receta</Button>
      </div>
    </form>
  )
}

function RecipeEditor({ id, onDone }: { id: number; onDone: () => void }) {
  const { data } = useQuery({ queryKey: ['recipe', id], queryFn: () => productionApi.recipe(id) })
  if (!data) return <SkeletonText lines={8} />
  return <RecipeForm recipe={data} onDone={onDone} />
}

export default function RecipesPage() {
  const can = useCan()
  const canManage = can('recipes.manage')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<number | 'new' | null>(null)
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['recipes', search, page], queryFn: () => productionApi.recipes({ search: search || undefined, page }),
    placeholderData: (prev) => prev,
  })
  const columns: Column<Recipe>[] = [
    { key: 'product', header: 'Producto', primary: true, cell: (r) => (
      <div><p className="font-medium text-ink">{r.product_name}</p>
        <p className="text-xs text-ink-muted">v{r.version} · {r.lines.length} ingredientes{r.consume_on_sale && ' · se descuenta al vender'}</p></div>
    ) },
    { key: 'yield', header: 'Rinde', align: 'right', cell: (r) => formatQty(r.yield_quantity, r.product_unit) },
    ...(can('catalog.view_costs') ? [
      { key: 'cost', header: 'Costo / unidad', align: 'right' as const, cell: (r: Recipe) => (
        r.cost ? <span className={r.cost.complete ? '' : 'text-warning'}>{formatUnitCost(r.cost.unit_cost)}</span> : '—') },
      { key: 'price', header: 'Precio', align: 'right' as const, hideOnMobile: true, cell: (r: Recipe) => formatCOP(r.product_price) },
      { key: 'margin', header: 'Margen', align: 'right' as const, cell: (r: Recipe) => (
        r.cost?.margin_pct ? `${Number(r.cost.margin_pct).toLocaleString('es-CO')} %` : <span className="text-ink-subtle">—</span>) },
    ] : []),
  ]
  return (
    <Page>
      <PageHeader title="Recetas" description="Qué lleva cada producto, cuánto rinde y cuánto cuesta producirlo"
                  actions={canManage && <Button icon={<Plus size={15} />} onClick={() => setEditing('new')}>Nueva receta</Button>} />
      <SearchInput label="Buscar recetas" placeholder="Producto" value={search} onChange={(v) => { setSearch(v); setPage(1) }} />
      <DataTable caption="Recetas" columns={columns} rows={data?.results} rowKey={(r) => r.id} isLoading={isLoading}
        onRowClick={canManage ? (r) => setEditing(r.id) : undefined}
        pagination={{ data, onPageChange: setPage, noun: 'recetas', isFetching }}
        empty={<EmptyState icon={<ChefHat size={20} />} title="Aún no hay recetas"
                           description="Con la receta, el sistema calcula el costo real de cada pan y descuenta los ingredientes al producir."
                           action={canManage ? { label: 'Crear receta', onClick: () => setEditing('new') } : undefined} />} />
      <Modal title={editing === 'new' ? 'Nueva receta' : 'Editar receta'} isOpen={editing !== null} onClose={() => setEditing(null)} size="xl">
        {editing === 'new' && <RecipeForm onDone={() => setEditing(null)} />}
        {typeof editing === 'number' && <RecipeEditor id={editing} onDone={() => setEditing(null)} />}
      </Modal>
    </Page>
  )
}
