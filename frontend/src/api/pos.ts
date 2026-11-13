import apiClient from './client'
import type { PaginatedResponse } from '@/types'

// ── Tipos ────────────────────────────────────────────────────────────────────
// Dinero y cantidades llegan como string decimal exacto. Los totales oficiales
// siempre los calcula el servidor; el POS solo muestra una vista previa.

export interface POSItem {
  id: number
  name: string
  code: string
  category: number | null
  unit: string
  unit_symbol: string
  price: string
  tax_rate: string
  price_with_tax: string
  stock: string
  tracks_stock: boolean
}

export interface POSCatalog {
  categories: { id: number; name: string }[]
  items: POSItem[]
}

export interface PaymentMethod {
  id: number
  code: string
  name: string
  kind: 'cash' | 'card' | 'transfer' | 'wallet'
}

export interface SaleLine {
  id: number
  item: number
  item_name: string
  unit_symbol: string
  quantity: string
  unit_price: string
  tax_rate: string
  line_subtotal: string
  tax_amount: string
  line_total: string
}

export interface SalePayment {
  id: number
  method: number
  method_name: string
  method_kind: PaymentMethod['kind']
  amount: string
  tendered: string
  reference: string
}

export interface SaleSummary {
  id: number
  number: string
  status: 'completed' | 'voided'
  created_at: string
  cashier_name: string
  customer_name: string
  total: string
  payment_summary: string
}

export interface Sale extends SaleSummary {
  location_name: string
  register_name: string
  subtotal: string
  tax_total: string
  discount: string
  change_given: string
  lines: SaleLine[]
  payments: SalePayment[]
  voided_at: string | null
  voided_by_name: string | null
  void_reason: string
  fiscal_status: string
  can_void: boolean
}

export interface SaleInput {
  client_uuid: string
  customer?: number | null
  discount?: string
  lines: { item: number; quantity: string }[]
  payments: { method: number; amount: string; reference?: string }[]
}

export interface CashRegister {
  id: number
  name: string
  location: number
  location_name: string
  is_active: boolean
  open_session_by: string | null
}

export interface CashMovement {
  id: number
  type: 'sale' | 'void' | 'income' | 'expense' | 'withdrawal'
  type_label: string
  amount: string
  reason: string
  sale_number: string | null
  created_by_name: string
  created_at: string
}

export interface CashSession {
  id: number
  register: number
  register_name: string
  status: 'open' | 'closed'
  opened_by_name: string
  opened_at: string
  opening_amount: string
  closed_by_name: string | null
  closed_at: string | null
  expected_amount: string | null
  counted_amount: string | null
  difference: string | null
  closing_note: string
}

export interface CashSessionDetail extends CashSession {
  denominations: Record<string, number>
  movements: CashMovement[]
  summary: {
    opening: string
    cash_sales: string
    voids: string
    income: string
    expenses: string
    withdrawals: string
    expected: string
    sales_count: number
    sales_total: string
    voided_count: number
    by_method: { method: string; kind: PaymentMethod['kind']; total: string }[]
    tolerance: string
  }
}

export interface SalesToday {
  date: string
  count: number
  total: string
  average_ticket: string
  voided: number
  gross_margin: string | null
  by_method: { method: string; total: string }[]
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const salesApi = {
  catalog: async (): Promise<POSCatalog> => (await apiClient.get<POSCatalog>('/sales/catalog/')).data,
  paymentMethods: async (): Promise<PaymentMethod[]> => (await apiClient.get<PaymentMethod[]>('/sales/payment-methods/')).data,
  create: async (payload: SaleInput): Promise<Sale> => (await apiClient.post<Sale>('/sales/', payload)).data,
  list: async (params?: { date?: string; status?: string; search?: string; session?: number; page?: number }) =>
    (await apiClient.get<PaginatedResponse<SaleSummary>>('/sales/', { params })).data,
  get: async (id: number): Promise<Sale> => (await apiClient.get<Sale>(`/sales/${id}/`)).data,
  void: async (id: number, reason: string): Promise<Sale> => (await apiClient.post<Sale>(`/sales/${id}/void/`, { reason })).data,
  today: async (): Promise<SalesToday> => (await apiClient.get<SalesToday>('/sales/today/')).data,
}

export const cashApi = {
  registers: async (): Promise<CashRegister[]> => (await apiClient.get<CashRegister[]>('/cash/registers/')).data,
  current: async (): Promise<CashSessionDetail | null> =>
    (await apiClient.get<{ session: CashSessionDetail | null }>('/cash/sessions/current/')).data.session,
  sessions: async (params?: { page?: number; status?: string }) =>
    (await apiClient.get<PaginatedResponse<CashSession>>('/cash/sessions/', { params })).data,
  session: async (id: number): Promise<CashSessionDetail> => (await apiClient.get<CashSessionDetail>(`/cash/sessions/${id}/`)).data,
  open: async (register: number, opening_amount: string): Promise<CashSessionDetail> =>
    (await apiClient.post<CashSessionDetail>('/cash/sessions/', { register, opening_amount })).data,
  addMovement: async (id: number, payload: { type: string; amount: string; reason: string }): Promise<CashMovement> =>
    (await apiClient.post<CashMovement>(`/cash/sessions/${id}/movements/`, payload)).data,
  close: async (id: number, payload: { counted_amount: string; denominations?: Record<string, number>; note?: string }) =>
    (await apiClient.post<CashSessionDetail>(`/cash/sessions/${id}/close/`, payload)).data,
}
