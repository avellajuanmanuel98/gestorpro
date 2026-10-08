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

export interface CategoryStock {
  categoria:  string
  stock:      number
  productos:  number
}

export interface LowStockProduct {
  id:            number
  name:          string
  code:          string
  stock:         number
  minimum_stock: number
}

export interface InventoryReport {
  by_category:      CategoryStock[]
  low_stock:        LowStockProduct[]
  total_productos:  number
  total_servicios:  number
  /** Valor a precio de venta (el valor a costo llegará con el libro de inventario) */
  valor_inventario: string
  valor_inventario_base: 'sale_price'
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
