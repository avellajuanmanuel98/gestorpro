import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { catalogApi, type ItemGroup, type ItemPayload } from '@/api/catalog'
import Alert from '@/components/ui/Alert'
import FormActions from '@/components/ui/FormActions'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import { SkeletonText } from '@/components/ui/Skeleton'
import Textarea from '@/components/ui/Textarea'
import { PRODUCT_KIND_OPTIONS, previewMargin } from '@/lib/catalog'
import { getErrorMessage } from '@/lib/errors'
import { useCan } from '@/store/authStore'
import { toast } from '@/store/toastStore'
import type { Category, Item, ItemKind, Unit } from '@/types'

const decimal = (max: number) => z.string().trim()
  .regex(new RegExp(`^\\d+([.,]\\d{1,${max}})?$`), 'Usa solo números (ej. 1800 o 12,5)')
const optionalDecimal = (max: number) => decimal(max).or(z.literal(''))

const schema = z.object({
  name: z.string().trim().min(2, 'Mínimo 2 caracteres'),
  code: z.string().trim(),
  description: z.string().optional(),
  kind: z.enum(['finished_good', 'resale', 'service', 'raw_material']),
  category: z.string(),
  unit: z.string().min(1),
  is_sellable: z.boolean(),
  price: optionalDecimal(2),
  tax_rate: z.string(),
  avg_cost: optionalDecimal(4),
  stock: optionalDecimal(4),
  minimum_stock: optionalDecimal(4),
  is_active: z.enum(['true', 'false']),
}).refine((d) => !d.is_sellable || (d.price !== '' && Number(d.price.replace(',', '.')) > 0), {
  path: ['price'], message: 'Indica el precio de venta',
})
type FormData = z.infer<typeof schema>

// Tarifas habituales en Colombia. El backend valida el rango (0–100).
const TAX_RATES = ['0', '5', '8', '19']
const num = (v: string) => v.replace(',', '.')
const plain = (v: string | undefined) => (v === undefined ? '' : String(Number(v)).replace('.', ','))

interface FormProps { group: ItemGroup; item?: Item; onSuccess: () => void; onCancel?: () => void }

/**
 * Los <select> no controlados toman su valor al montarse: si las opciones
 * (unidades, categorías) llegaran después, mostrarían la primera opción y al
 * guardar se cambiaría la unidad del ítem. Por eso el formulario se monta solo
 * cuando las opciones ya están cargadas.
 */
export default function ItemForm(props: FormProps) {
  const isIngredientScreen = props.group === 'ingredients'
  const units = useQuery({ queryKey: ['units'], queryFn: catalogApi.units, staleTime: Infinity })
  const categories = useQuery({
    queryKey: ['categories', 'select', props.group],
    queryFn: () => catalogApi.listCategories({ kind: isIngredientScreen ? 'ingredient' : 'product', page_size: 100 }),
  })
  if (units.isError || categories.isError) return <Alert tone="danger">No se pudieron cargar las opciones del formulario.</Alert>
  if (!units.data || !categories.data) return <SkeletonText lines={8} />
  return <ItemFormFields {...props} units={units.data} categories={categories.data.results} />
}

function ItemFormFields({ group, item, onSuccess, onCancel, units, categories }: FormProps & { units: Unit[]; categories: Category[] }) {
  const queryClient = useQueryClient()
  const canSeeCosts = useCan()('catalog.view_costs')
  const isIngredientScreen = group === 'ingredients'

  const { register, handleSubmit, control, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: item?.name ?? '', code: item?.code ?? '', description: item?.description ?? '',
      kind: item?.kind ?? (isIngredientScreen ? 'raw_material' : 'finished_good'),
      category: item?.category ? String(item.category) : '',
      unit: item?.unit ?? (isIngredientScreen ? 'kg' : 'und'),
      is_sellable: item?.is_sellable ?? !isIngredientScreen,
      price: item && Number(item.price) > 0 ? plain(item.price) : '',
      tax_rate: item ? String(Number(item.tax_rate)) : isIngredientScreen ? '0' : '19',
      avg_cost: item?.avg_cost !== undefined && Number(item.avg_cost) > 0 ? plain(item.avg_cost) : '',
      stock: item ? plain(item.stock) : '', minimum_stock: item ? plain(item.minimum_stock) : '',
      is_active: item?.is_active === false ? 'false' : 'true',
    },
  })
  const [kind, unitCode, sellable, price, cost] = useWatch({
    control, name: ['kind', 'unit', 'is_sellable', 'price', 'avg_cost'],
  })
  const isService = kind === 'service'
  const unit = units.find((u) => u.code === unitCode)
  const margin = previewMargin(num(price), num(cost))
  const noun = isIngredientScreen ? 'ingrediente' : 'producto'

  const mutation = useMutation({
    mutationFn: (d: FormData) => {
      const payload: ItemPayload = {
        name: d.name, code: d.code, description: d.description, kind: d.kind as ItemKind,
        category: d.category ? Number(d.category) : null, unit: d.kind === 'service' ? 'und' : d.unit,
        is_sellable: d.is_sellable, is_active: d.is_active === 'true',
        price: d.is_sellable ? num(d.price) : '0', tax_rate: d.is_sellable ? d.tax_rate : '0',
        stock: num(d.stock) || '0', minimum_stock: num(d.minimum_stock) || '0',
        // Sin permiso de costos el campo no se envía (el servidor lo rechazaría)
        ...(canSeeCosts ? { avg_cost: num(d.avg_cost) || '0' } : {}),
      }
      return item ? catalogApi.updateItem(item.id, payload) : catalogApi.createItem(payload)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['items'] })
      queryClient.invalidateQueries({ queryKey: ['low-stock'] })
      toast.success(item ? `«${saved.name}» actualizado` : `«${saved.name}» agregado (${saved.code})`)
      onSuccess()
    },
  })

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-5" noValidate>
      <div className="grid sm:grid-cols-[1fr_170px] gap-4">
        <Input label="Nombre" required autoFocus {...register('name')} error={errors.name?.message}
               placeholder={isIngredientScreen ? 'Harina de trigo' : 'Pan de bono'} />
        <Input label="Código" placeholder="Automático" {...register('code')} error={errors.code?.message}
               hint={item ? undefined : 'Déjalo vacío y se asigna solo.'} />
      </div>

      {!isIngredientScreen && (
        <fieldset>
          <legend className="text-sm font-medium text-ink mb-2">¿Qué tipo de producto es?</legend>
          <div className="grid sm:grid-cols-3 gap-2">
            {PRODUCT_KIND_OPTIONS.map((o) => (
              <label key={o.value} className="flex gap-2.5 rounded-xl border border-line-strong p-3 cursor-pointer
                                               has-[:checked]:border-primary has-[:checked]:bg-primary-soft/60">
                <input type="radio" value={o.value} {...register('kind')} className="mt-0.5 accent-[var(--primary)]" />
                <span><span className="block text-sm font-medium text-ink">{o.label}</span>
                  <span className="block text-xs text-ink-muted leading-snug">{o.hint}</span></span>
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        <Select label="Categoría" {...register('category')}>
          <option value="">Sin categoría</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
        <Select label={isIngredientScreen ? 'Unidad de medida' : 'Se vende por'} {...register('unit')}
                hint={isIngredientScreen ? 'Existencias y costo se expresan en esta unidad.' : undefined}>
          {units.filter((u) => isService ? u.code === 'und' : isIngredientScreen || (u.code !== 'g' && u.code !== 'ml')).map((u) => (
            <option key={u.code} value={u.code}>{u.name}</option>
          ))}
        </Select>
      </div>

      {isIngredientScreen && (
        <label className="flex items-start gap-2.5 text-sm text-ink cursor-pointer">
          <input type="checkbox" {...register('is_sellable')} className="mt-0.5 accent-[var(--primary)]" />
          <span>También lo vendo directamente
            <span className="block text-xs text-ink-muted">Por ejemplo, el queso que se vende por libra.</span></span>
        </label>
      )}

      {(sellable || canSeeCosts) && (
        <div className="grid sm:grid-cols-3 gap-4 rounded-xl bg-surface-muted/60 p-4">
          {sellable && (
            <>
              <Input label={`Precio por ${unit?.symbol ?? 'unidad'}`} required inputMode="decimal" {...register('price')}
                     error={errors.price?.message} hint="Sin IVA." />
              <Select label="IVA" {...register('tax_rate')}>
                {TAX_RATES.map((r) => <option key={r} value={r}>{r} %</option>)}
              </Select>
            </>
          )}
          {canSeeCosts && !isService && (
            <Input label={`Costo por ${unit?.symbol ?? 'unidad'}`} inputMode="decimal" {...register('avg_cost')}
                   error={errors.avg_cost?.message}
                   hint={sellable && margin !== null ? `Margen: ${margin.toLocaleString('es-CO')} %` : 'Costo de referencia.'} />
          )}
        </div>
      )}

      {!isService && (
        <div className="grid sm:grid-cols-2 gap-4">
          <Input label={`Existencia actual (${unit?.symbol ?? ''})`} inputMode="decimal" {...register('stock')}
                 error={errors.stock?.message} placeholder="0" />
          <Input label={`Existencia mínima (${unit?.symbol ?? ''})`} inputMode="decimal" {...register('minimum_stock')}
                 error={errors.minimum_stock?.message} placeholder="0" hint="Por debajo verás una alerta." />
        </div>
      )}

      <Textarea label="Descripción" rows={2} {...register('description')} />
      <Select label="Estado" {...register('is_active')}>
        <option value="true">Activo</option>
        <option value="false">Inactivo</option>
      </Select>
      <FormActions error={mutation.isError ? getErrorMessage(mutation.error) : null} submitting={mutation.isPending}
                   submitLabel={item ? 'Guardar cambios' : `Crear ${noun}`} onCancel={onCancel} />
    </form>
  )
}
