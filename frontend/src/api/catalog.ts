import apiClient from './client'
import type { Category, CategoryKind, Item, ItemKind, PaginatedResponse, Unit } from '@/types'

export type ItemGroup = 'products' | 'ingredients'

export interface ItemListParams {
  group?: ItemGroup
  kind?: ItemKind
  search?: string
  category?: number
  is_active?: boolean
  is_sellable?: boolean
  low_stock?: 'true'
  page?: number
  page_size?: number
}

/** Lo que se envía al crear o editar: el servidor valida y completa el resto. */
export type ItemPayload = Partial<Pick<Item,
  'name' | 'code' | 'description' | 'kind' | 'category' | 'unit' | 'is_sellable' | 'price' | 'tax_rate'
  | 'avg_cost' | 'stock' | 'minimum_stock' | 'is_active'>>

export const catalogApi = {
  units: async (): Promise<Unit[]> => (await apiClient.get<Unit[]>('/catalog/units/')).data,

  // ── Ítems (productos e ingredientes) ───────────────────────────────────────
  listItems: async (params?: ItemListParams) =>
    (await apiClient.get<PaginatedResponse<Item>>('/catalog/items/', { params })).data,

  getItem: async (id: number): Promise<Item> => (await apiClient.get<Item>(`/catalog/items/${id}/`)).data,

  createItem: async (payload: ItemPayload): Promise<Item> =>
    (await apiClient.post<Item>('/catalog/items/', payload)).data,

  updateItem: async (id: number, payload: ItemPayload): Promise<Item> =>
    (await apiClient.patch<Item>(`/catalog/items/${id}/`, payload)).data,

  deleteItem: async (id: number): Promise<void> => {
    await apiClient.delete(`/catalog/items/${id}/`)
  },

  /** Productos e ingredientes activos en o por debajo de su mínimo */
  lowStock: async (params?: { group?: ItemGroup; page_size?: number }) =>
    (await apiClient.get<PaginatedResponse<Item>>('/catalog/low-stock/', { params })).data,

  /** Panaderías: carga los ingredientes comunes (sin costos). Idempotente. */
  loadStarterCatalog: async (): Promise<{ created: number }> =>
    (await apiClient.post<{ created: number }>('/bakery/starter-catalog/')).data,

  // ── Categorías ─────────────────────────────────────────────────────────────
  listCategories: async (params?: { kind?: CategoryKind; page?: number; page_size?: number }) =>
    (await apiClient.get<PaginatedResponse<Category>>('/catalog/categories/', { params })).data,

  createCategory: async (payload: Partial<Category>): Promise<Category> =>
    (await apiClient.post<Category>('/catalog/categories/', payload)).data,

  updateCategory: async (id: number, payload: Partial<Category>): Promise<Category> =>
    (await apiClient.patch<Category>(`/catalog/categories/${id}/`, payload)).data,

  deleteCategory: async (id: number): Promise<void> => {
    await apiClient.delete(`/catalog/categories/${id}/`)
  },
}
