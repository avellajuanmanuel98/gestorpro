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
  /** Plan y funcionalidades: solo para la UI; el backend las valida. */
  plan: PlanInfo | null
  features: string[]
}

export interface PlanInfo {
  code: string | null
  name: string | null
  status: 'trialing' | 'active' | 'past_due' | 'canceled' | null
  trial_ends_at: string | null
}

export interface PlanSummary {
  plan: PlanInfo
  features: string[]
  limits: { key: string; label: string; used: number; limit: number | null }[]
}

// ── Usuarios, roles y auditoría ──────────────────
export interface RoleSummary {
  id: number
  code: string
  name: string
}

export interface Member {
  id: number
  email: string
  full_name: string
  role: RoleSummary
  is_owner: boolean
  status: 'active' | 'invited' | 'suspended'
  last_login: string | null
  created_at: string
}

export interface Invitation {
  id: number
  email: string
  role: RoleSummary
  status: 'pending' | 'accepted' | 'expired' | 'revoked'
  expires_at: string
  invited_by: string | null
  created_at: string
  /** Solo en la respuesta de creación: el enlace no se puede volver a consultar */
  invite_url?: string
}

export interface Role {
  id: number
  code: string
  name: string
  is_system: boolean
  grants_all: boolean
  /** ['*'] para el propietario */
  permissions: string[]
  members_count: number
}

export interface PermissionDef {
  code: string
  module: string
  description: string
  /** false si el módulo no está incluido en el plan */
  available: boolean
}

export interface AuditEntry {
  id: number
  created_at: string
  actor: number | null
  actor_label: string
  action: string
  entity_type: string
  entity_id: string
  summary: string
  changes: Record<string, [unknown, unknown]>
  ip: string | null
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
export type CategoryKind = 'product' | 'ingredient'

export interface Category {
  id: number
  name: string
  description: string
  kind: CategoryKind
  items_count: number
  created_at: string
}

/** Unidad de medida global (g, kg, l, und…). */
export interface Unit {
  code: string
  name: string
  symbol: string
  dimension: 'mass' | 'volume' | 'count'
  factor: string
}

/**
 * Producto elaborado, reventa, servicio o ingrediente. Cantidades y dinero
 * llegan como string (Decimal exacto). Los campos de costo solo llegan si el
 * usuario tiene `catalog.view_costs`.
 */
export type ItemKind = 'finished_good' | 'resale' | 'raw_material' | 'service'

export interface Item {
  id: number
  name: string
  code: string
  description?: string
  kind: ItemKind
  category: number | null
  category_name: string | null
  unit: string
  unit_symbol: string
  is_sellable: boolean
  price: string
  tax_rate: string
  avg_cost?: string
  margin_pct?: string | null
  stock: string
  minimum_stock: string
  is_low_stock: boolean
  stock_value?: string
  consume_on_sale: boolean
  is_active: boolean
  created_by?: string
  created_at?: string
  updated_at?: string
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
