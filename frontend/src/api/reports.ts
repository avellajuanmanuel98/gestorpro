import apiClient from './client'

// ── Tipos de respuesta ────────────────────────────────────────────────────────

// Importes como string decimal exacto (ver lib/money.ts)
export interface MonthlyTrendPoint {
  month: string
  mes:   string
  total: string
  count: number
}

export interface StatusBreakdown {
  status: string
  label:  string
  count:  number
  total:  string
}

export interface TopClient {
  name:  string
  total: string
  count: number
}

export interface BillingReport {
  monthly_trend:    MonthlyTrendPoint[]
  status_breakdown: StatusBreakdown[]
  top_clients:      TopClient[]
}

export interface CategoryValue {
  categoria: string
  grupo:     'productos' | 'ingredientes'
  items:     number
  /** Valor a costo; null si el usuario no puede ver costos */
  valor:     string | null
}

export interface LowStockItem {
  id:            number
  name:          string
  code:          string
  stock:         string
  minimum_stock: string
  unit:          string
}

export interface InventoryReport {
  by_category:        CategoryValue[]
  low_stock:          LowStockItem[]
  total_productos:    number
  total_ingredientes: number
  /** Valores a COSTO (existencia × costo por unidad); null sin permiso `catalog.view_costs` */
  valor_productos:    string | null
  valor_ingredientes: string | null
  valor_inventario:   string | null
  valor_inventario_base: 'cost'
}

export interface DepartmentCount {
  departamento: string
  total:        number
}

export interface SupplierCategory {
  categoria: string
  total:     number
}

export interface HRReport {
  by_department:         DepartmentCount[]
  employees_active:      number
  employees_inactive:    number
  suppliers_by_category: SupplierCategory[]
}

// ── API ───────────────────────────────────────────────────────────────────────

export const reportsApi = {
  billing:   async (): Promise<BillingReport>   => (await apiClient.get('/reports/billing/')).data,
  inventory: async (): Promise<InventoryReport> => (await apiClient.get('/reports/inventory/')).data,
  hr:        async (): Promise<HRReport>        => (await apiClient.get('/reports/hr/')).data,
}
