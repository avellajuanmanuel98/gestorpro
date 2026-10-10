import apiClient from './client'

/** Períodos que entiende el backend; todos se comparan contra el período equivalente anterior. */
export type PeriodPreset = 'today' | 'yesterday' | '7d' | '30d' | 'this_month' | 'last_month' | 'this_year' | 'custom'

export interface PeriodQuery {
  period: PeriodPreset
  from?: string
  to?: string
  location?: number
}

export interface PeriodInfo {
  preset: PeriodPreset
  from: string
  to: string
  label: string
  days: number
  previous: { from: string; to: string; label: string }
}

/** Valor del período, del comparable y variación %. `change_pct` es null si no hay base: se muestra "—". */
export interface Kpi<T = string> {
  value: T | null
  previous: T | null
  change_pct: number | null
}

export interface AttentionItem {
  kind: 'low_stock' | 'negative_stock' | 'stale_cash'
  tone: 'warning' | 'danger'
  count: number
  detail: string
  to: string
}

export interface Summary {
  period: PeriodInfo
  kpis: {
    sales: Kpi
    transactions: Kpi<number>
    average_ticket: Kpi
    // Solo con permiso de costos:
    gross_profit?: Kpi
    cost_of_sales?: Kpi
    waste_cost?: Kpi
    gross_margin_pct?: number | null
    waste_pct_of_cost?: number | null
  }
  attention: AttentionItem[]
}

export interface HourPoint { hour: number; sales: string; transactions: number; previous_sales: string }

export type BreakdownBy = 'day' | 'weekday' | 'method' | 'cashier' | 'category'
export interface BreakdownRow { key: string | number; label: string; sales: string; transactions: number }

export type Quadrant = 'star' | 'workhorse' | 'puzzle' | 'dog'
export interface ProductRow {
  item: number
  name: string
  category: string | null
  unit: string
  units: string
  revenue: string
  produced: string
  wasted: string
  waste_rate_pct: number | null
  cost?: string
  gross_profit?: string
  margin_pct?: number | null
  unit_margin?: string | null
  quadrant?: Quadrant
  quadrant_label?: string
  quadrant_advice?: string
}

export interface CashSessionRow {
  id: number
  register: string
  cashier: string
  opened_at: string
  closed_at: string | null
  status: 'open' | 'closed'
  expected: string | null
  counted: string | null
  difference: string | null
  note: string
}

export interface CashReport {
  period: PeriodInfo
  sessions: CashSessionRow[]
  by_cashier: { cashier: string; sessions: number; with_difference: number; net_difference: string }[]
}

export interface CoverageRow { item: number; name: string; unit: string; stock: string; daily_usage: string; days_left: number }

export interface WasteSummary {
  period: PeriodInfo
  total_cost: string | null
  by_reason: { reason: string; records: number; cost: string | null }[]
  by_item: { item: string; unit: string; quantity: string; cost: string | null }[]
}

export interface SuggestionRow {
  item: number
  name: string
  unit: string
  history: string[]
  average_sold: string
  average_wasted: string
  stock: string
  suggested: string
  recipe: number | null
  batches: number | null
  batch_size: string | null
}

export interface ProductionSuggestion { target: string; weeks_with_data: number; rows: SuggestionRow[] }

const get = async <T>(url: string, params?: object): Promise<T> => (await apiClient.get<T>(url, { params })).data

/** Descarga el CSV que genera el servidor (mismos filtros que la pantalla). */
async function downloadCsv(url: string, params: object) {
  const res = await apiClient.get<Blob>(url, { params: { ...params, export: 'csv' }, responseType: 'blob' })
  const match = /filename="?([^";]+)"?/.exec(String(res.headers['content-disposition'] ?? ''))
  const href = URL.createObjectURL(res.data)
  const a = Object.assign(document.createElement('a'), { href, download: match?.[1] ?? 'reporte.csv' })
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(href)
}

export const analyticsApi = {
  summary: (q: PeriodQuery) => get<Summary>('/analytics/summary/', q),
  hourly: (q: PeriodQuery) => get<{ period: PeriodInfo; hours: HourPoint[] }>('/analytics/hourly/', q),
  breakdown: (q: PeriodQuery, by: BreakdownBy) =>
    get<{ period: PeriodInfo; by: BreakdownBy; rows: BreakdownRow[] }>('/analytics/breakdown/', { ...q, by }),
  products: (q: PeriodQuery) => get<{ period: PeriodInfo; rows: ProductRow[]; costs: boolean }>('/analytics/products/', q),
  cash: (q: PeriodQuery) => get<CashReport>('/analytics/cash/', q),
  coverage: () => get<{ rows: CoverageRow[] }>('/analytics/coverage/'),
  waste: (q: PeriodQuery) => get<WasteSummary>('/waste/summary/', q),
  suggestion: (date?: string) => get<ProductionSuggestion>('/bakery/production-suggestion/', date ? { date } : undefined),
  exportCsv: (report: 'breakdown' | 'products' | 'cash', q: PeriodQuery, extra: object = {}) =>
    downloadCsv(`/analytics/${report}/`, { ...q, ...extra }),
}
