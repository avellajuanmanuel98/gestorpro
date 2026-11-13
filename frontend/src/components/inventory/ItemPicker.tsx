import { catalogApi, type ItemListParams } from '@/api/catalog'
import Combobox, { type ComboOption } from '@/components/ui/Combobox'
import type { Item } from '@/types'

export type ItemOption = ComboOption & { item: Item }

/** Selector de ítems con búsqueda en el servidor (productos o ingredientes según `params`). */
export default function ItemPicker({ label, value, onChange, params, queryKey, placeholder, required }: {
  label?: string
  value: ItemOption | null
  onChange: (option: ItemOption | null) => void
  params: ItemListParams
  queryKey: string
  placeholder?: string
  required?: boolean
}) {
  const search = async (term: string): Promise<ItemOption[]> => {
    const res = await catalogApi.listItems({ ...params, search: term || undefined, is_active: true, page_size: 20 })
    return res.results.map((item) => ({ id: item.id, label: item.name, description: `${item.code} · ${item.unit_symbol}`, item }))
  }
  return (
    <Combobox label={label} value={value} required={required} placeholder={placeholder ?? 'Buscar…'} queryKey={queryKey}
              search={search} onChange={(o) => onChange(o as ItemOption | null)} />
  )
}
