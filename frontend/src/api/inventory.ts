import apiClient from './client'
import type { PaginatedResponse } from '@/types'

// ── Libro de inventario ──────────────────────────────────────────────────────

export type MovementType = 'opening' | 'purchase' | 'sale' | 'sale_void' | 'production_consume'
  | 'production_output' | 'waste' | 'adjustment_in' | 'adjustment_out'

export interface StockMovement {
  id: number
  item: number
  item_name: string
  unit_symbol: string
  location_name: string
  type: MovementType
  type_label: string
  quantity: string
  unit_cost?: string
  total_cost?: string
  balance_after: string
  avg_cost_after?: string
  source_type: string
  source_id: number | null
  source_label: string
  reason: string
  created_by_name: string | null
  created_at: string
}

// ── Compras ──────────────────────────────────────────────────────────────────

export interface PurchaseSummary {
  id: number
  number: string
  supplier: number | null
  supplier_name: string | null
  supplier_invoice: string
  received_on: string
  total: string
  notes: string
  created_by_name: string
  created_at: string
  lines_count: number
}

export interface Purchase extends PurchaseSummary {
  lines: { id: number; item: number; item_name: string; quantity: string; unit_symbol: string; unit_cost: string;
           total: string; base_quantity: string; item_unit_symbol: string; base_unit_cost: string }[]
}

export interface PurchaseInput {
  supplier?: number | null
  supplier_invoice?: string
  received_on: string
  notes?: string
  lines: { item: number; quantity: string; unit: string; unit_cost: string }[]
}

// ── Recetas y producción ─────────────────────────────────────────────────────

export interface RecipeLine {
  id: number
  ingredient: number
  ingredient_name: string
  quantity: string
  unit: string
  unit_symbol: string
  waste_pct: string
  ingredient_unit: string
  ingredient_unit_code: string
  base_quantity: string
  cost?: string
  ingredient_avg_cost?: string
  missing_cost?: boolean
}

export interface Recipe {
  id: number
  product: number
  product_name: string
  product_unit: string
  product_price: string
  consume_on_sale: boolean
  version: number
  is_active: boolean
  yield_quantity: string
  notes: string
  lines: RecipeLine[]
  cost: { total: string; unit_cost: string; margin_pct: string | null; complete: boolean } | null
  created_at: string
  updated_at: string
}

export interface RecipeInput {
  product: number
  yield_quantity: string
  notes?: string
  lines: { ingredient: number; quantity: string; unit: string; waste_pct?: string }[]
}

export interface ProductionPlan {
  recipe: number
  quantity: string
  lines: { ingredient: number; name: string; unit_symbol: string; quantity: string; stock: string; short: boolean;
           cost?: string }[]
  estimated_cost: string | null
  estimated_unit_cost: string | null
}

export interface Batch {
  id: number
  number: string
  product: number
  product_name: string
  unit_symbol: string
  recipe: number
  recipe_version: number
  produced_quantity: string
  total_cost?: string
  unit_cost?: string
  notes: string
  created_by_name: string
  created_at: string
  consumptions: { ingredient: number; ingredient_name: string; unit_symbol: string; planned_quantity: string;
                  actual_quantity: string; unit_cost?: string; total_cost?: string }[]
}

// ── Mermas ───────────────────────────────────────────────────────────────────

export interface WasteReason { id: number; code: string; name: string }

export interface WasteRecord {
  id: number
  item: number
  item_name: string
  unit_symbol: string
  quantity: string
  reason: number
  reason_name: string
  unit_cost?: string
  total_cost?: string
  notes: string
  created_by_name: string
  created_at: string
}

export const inventoryApi = {
  movements: async (params?: { item?: number; type?: string; date_from?: string; date_to?: string; page?: number }) =>
    (await apiClient.get<PaginatedResponse<StockMovement>>('/inventory/movements/', { params })).data,
  count: async (payload: { counts: { item: number; counted: string }[]; note?: string }) =>
    (await apiClient.post<{ adjustments: StockMovement[] }>('/inventory/counts/', payload)).data,
}

export const purchasesApi = {
  list: async (params?: { page?: number; search?: string }) =>
    (await apiClient.get<PaginatedResponse<PurchaseSummary>>('/purchases/', { params })).data,
  get: async (id: number) => (await apiClient.get<Purchase>(`/purchases/${id}/`)).data,
  create: async (payload: PurchaseInput) => (await apiClient.post<Purchase>('/purchases/', payload)).data,
}

export const productionApi = {
  recipes: async (params?: { page?: number; search?: string; page_size?: number }) =>
    (await apiClient.get<PaginatedResponse<Recipe>>('/production/recipes/', { params })).data,
  recipe: async (id: number) => (await apiClient.get<Recipe>(`/production/recipes/${id}/`)).data,
  saveRecipe: async (payload: RecipeInput) => (await apiClient.post<Recipe>('/production/recipes/', payload)).data,
  plan: async (id: number, quantity: string) =>
    (await apiClient.get<ProductionPlan>(`/production/recipes/${id}/plan/`, { params: { quantity } })).data,
  batches: async (params?: { page?: number }) =>
    (await apiClient.get<PaginatedResponse<Batch>>('/production/batches/', { params })).data,
  produce: async (payload: { recipe: number; quantity: string; actual?: Record<string, string>; notes?: string }) =>
    (await apiClient.post<Batch>('/production/batches/', payload)).data,
}

export const wasteApi = {
  reasons: async () => (await apiClient.get<WasteReason[]>('/waste/reasons/')).data,
  list: async (params?: { page?: number; date_from?: string; date_to?: string }) =>
    (await apiClient.get<PaginatedResponse<WasteRecord> & { total_cost?: string }>('/waste/', { params })).data,
  create: async (payload: { item: number; quantity: string; reason: number; notes?: string }) =>
    (await apiClient.post<WasteRecord>('/waste/', payload)).data,
}
