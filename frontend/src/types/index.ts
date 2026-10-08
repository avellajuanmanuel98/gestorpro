// ── Sesión ───────────────────────────────────────
export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  avatar: string | null
  is_platform_admin: boolean
  date_joined: string
}

export interface SessionTenant {
  id: number
  name: string
  slug: string
  vertical: 'generic' | 'bakery'
}

export interface Session {
  user: User
  tenant: SessionTenant | null
  role: { code: string; name: string } | null
  /** Solo para adaptar la UI. El backend valida cada permiso. */
  permissions: string[]
  memberships: { tenant_id: number; tenant_name: string; role: string }[]
}

export interface AuthTokens {
  access: string
  refresh: string
}

// ── Empresa ──────────────────────────────────────
export interface Tenant {
  id: number
  name: string
  legal_name: string
  slug: string
  tax_id: string
  vertical: 'generic' | 'bakery'
  status: 'active' | 'suspended'
  email: string
  phone: string
  address: string
  city: string
  logo: string | null
  timezone: string
  currency: string
  created_at: string
}

// ── Clientes ─────────────────────────────────────
export interface Customer {
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
  category_name: string | null
  price: string
  tax_rate: string
  stock: number
  minimum_stock: number
  is_low_stock: boolean
  is_active: boolean
  created_by: string
  created_at: string
  updated_at: string
}

// ── Facturación ──────────────────────────────────
/** Línea calculada por el servidor (precio e impuesto vienen del catálogo). */
export interface InvoiceLine {
  id: number
  product: number
  product_name: string
  description: string
  quantity: string
  unit_price: string
  tax_rate: string
  line_subtotal: string
  tax_amount: string
  line_total: string
}

/** Lo que el cliente puede pedir al crear/editar. Los importes los calcula el backend. */
export interface InvoiceLineInput {
  product: number
  quantity: string | number
  unit_price?: string | number
  description?: string
}

export interface Invoice {
  id: number
  number: string
  invoice_type: 'quote' | 'invoice'
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
  customer: number
  customer_name: string
  issue_date: string
  due_date: string
  subtotal: string
  tax_amount: string
  discount: string
  total: string
  notes: string
  lines: InvoiceLine[]
  created_by: string
  created_at: string
  updated_at: string
}

export type InvoiceInput = Pick<Invoice, 'number' | 'invoice_type' | 'customer' | 'issue_date' | 'due_date' | 'notes'> & {
  status?: Invoice['status']
  discount?: string | number
  items?: InvoiceLineInput[]
}

export interface BillingSummary {
  total_invoices: number
  total_quotes: number
  paid_total: string
  pending_total: string
  overdue_count: number
}

// ── Empleados ────────────────────────────────────
export interface Employee {
  id: number
  document_type: 'CC' | 'CE' | 'PP'
  document_number: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  address: string
  city: string
  position: string
  department: 'admin' | 'sales' | 'operations' | 'finance' | 'it' | 'hr' | 'other'
  hire_date: string
  /** Ausente si el usuario no tiene el permiso hr.view_salary */
  salary?: string | null
  status: 'active' | 'inactive'
  notes: string
  created_by: string
  created_at: string
  updated_at: string
}

// ── Proveedores ──────────────────────────────────
export interface Supplier {
  id: number
  company_name: string
  contact_name: string
  document_type: 'NIT' | 'CC' | 'CE' | 'PP'
  document_number: string
  email: string
  phone: string
  address: string
  city: string
  website: string
  category: 'materials' | 'services' | 'technology' | 'logistics' | 'marketing' | 'other'
  status: 'active' | 'inactive'
  notes: string
  created_by: string
  created_at: string
  updated_at: string
}

// ── Paginación ───────────────────────────────────
// Todos los listados del backend devuelven esta estructura
export interface PaginatedResponse<T> {
  count: number
  page: number
  page_size: number
  total_pages: number
  next: string | null
  previous: string | null
  results: T[]
}
