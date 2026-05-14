import apiClient from './client'

// ── Tipos de respuesta ────────────────────────────────────────────────────────

export interface MonthlyTrendPoint {
  mes:   string
  total: number
  count: number
}

export interface StatusBreakdown {
  status: string
  label:  string
  count:  number
  total:  number
}

export interface TopClient {
  name:  string
  total: number
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
  valor_inventario: number
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
