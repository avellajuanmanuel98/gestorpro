// ── Auth ─────────────────────────────────────────
export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: 'admin' | 'employee'
  avatar: string | null
  date_joined: string
}

// ── Empresa ──────────────────────────────────────
export interface Company {
  id: number
  name: string
  slug: string
  plan: 'free' | 'starter' | 'pro'
  email: string
  phone: string
  address: string
  city: string
  nit: string
  logo: string | null
  is_active: boolean
  created_at: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

// ── Clientes ─────────────────────────────────────
export interface Client {
  id: number
  document_type: 'CC' | 'NIT' | 'CE' | 'PP'
  document_number: string
  first_name: string
  last_name: string
  full_name: string
  company_name: string
  email: string
  phone: string
  address: string
  city: string
  status: 'active' | 'inactive'
  notes: string
  created_by: string
  created_at: string
  updated_at: string
}

// ── Inventario ───────────────────────────────────
export interface Category {
  id: number
  name: string
  description: string
  products_count: number
  created_at: string
}

export interface Product {
  id: number
  name: string
  code: string
  description: string
  product_type: 'product' | 'service'
  category: number | null
  category_name: string
  price: string
  tax_rate: string
  price_with_tax: string
  stock: number
  minimum_stock: number
  is_low_stock: boolean
  is_active: boolean
  created_by: string
  created_at: string
  updated_at: string
}

// ── Facturación ──────────────────────────────────
export interface InvoiceItem {
  id: number
  product: number
  product_name: string
  description: string
  quantity: string
  unit_price: string
  tax_rate: string
  line_total: string
  tax_amount: string
  line_total_with_tax: string
}

export interface Invoice {
  id: number
  number: string
  invoice_type: 'quote' | 'invoice'
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
  client: number
  client_name: string
  issue_date: string
  due_date: string
  subtotal: string
  tax_amount: string
  discount: string
  total: string
  notes: string
  items: InvoiceItem[]
  created_by: string
  created_at: string
  updated_at: string
}

export interface BillingSummary {
  total_invoices: number
  total_quotes: number
  paid_total: string
  pending_total: string
  overdue_count: number
}

// ── Paginación ───────────────────────────────────
// Django devuelve esta estructura en todos los listados
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
