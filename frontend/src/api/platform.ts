import apiClient from './client'
import type { PaginatedResponse as Paginated } from '@/types'

export type SubscriptionStatus = 'trialing' | 'trial_expired' | 'active' | 'past_due' | 'canceled'

export interface PlatformOverview {
  tenants: { total: number; active: number; suspended: number; new_30d: number; in_use_7d: number; by_vertical: Record<string, number> }
  subscriptions: {
    by_status: Partial<Record<SubscriptionStatus | 'none', number>>
    by_plan: { code: string; name: string; count: number }[]
    /** Ingreso mensual recurrente estimado: suma del precio de los planes de suscripciones activas */
    mrr: string
    active_without_price: number
  }
  users: number
  sales_30d: number
  signups: { month: string; new_tenants: number }[]
  trials_ending: { id: number; name: string; trial_ends_at: string }[]
  attention: { id: number; name: string; kind: SubscriptionStatus }[]
}

export interface PlatformTenant {
  id: number
  name: string
  slug: string
  vertical: 'generic' | 'bakery'
  status: 'active' | 'suspended'
  city: string
  tax_id: string
  email: string
  phone: string
  modules: string[]
  created_at: string
  plan: { code: string; name: string } | null
  subscription_status: SubscriptionStatus | null
  trial_ends_at: string | null
  current_period_end: string | null
  members: number | null
  last_activity: string | null
  last_sale: string | null
}

export type TenantMember = { email: string; name: string; role: string; status: string; last_login: string | null }

/** Detalle: en la lista `members` es un conteo; aquí, las personas. */
export interface PlatformTenantFull extends Omit<PlatformTenant, 'members'> {
  members: TenantMember[]
  usage: { key: string; label: string; used: number; limit: number | null }[]
  features: string[]
  locations: number
  products: number
  support_sessions: { id: number; agent: string; reason: string; started_at: string; expires_at: string; ended_at: string | null; requests: number }[]
  events: { id: number; action: string; summary: string; actor: string; created_at: string }[]
}

export interface PlatformPlan {
  id: number
  code: string
  name: string
  description: string
  price_monthly: string | null
  currency: string
  is_public: boolean
  is_active: boolean
  sort: number
  features: string[]
  limits: Record<string, number | null>
  subscribers: number
}

export interface PlatformEvent {
  id: number
  action: string
  summary: string
  actor_label: string
  tenant: number | null
  tenant_name: string | null
  details: Record<string, unknown>
  ip: string | null
  created_at: string
}

export interface SupportGrant { access: string; expires_at: string; session: number; tenant: { id: number; name: string } }

export const VERTICAL_LABEL = { bakery: 'Miga (panadería)', generic: 'GestorPro (general)' } as const

export const FEATURE_LABELS: Record<string, string> = {
  'module.hr': 'Módulo de personal', 'module.assistant': 'Asistente de IA', custom_roles: 'Roles personalizados',
}
export const LIMIT_LABELS: Record<string, string> = {
  users: 'Usuarios', locations: 'Sucursales', products: 'Productos', custom_roles: 'Roles personalizados',
}

export const platformApi = {
  overview: async () => (await apiClient.get<PlatformOverview>('/platform/overview/')).data,
  tenants: async (params: object) => (await apiClient.get<Paginated<PlatformTenant>>('/platform/tenants/', { params })).data,
  tenant: async (id: number) => (await apiClient.get<PlatformTenantFull>(`/platform/tenants/${id}/`)).data,
  onboard: async (body: { name: string; owner_email: string; vertical: string; plan: string; city?: string; tax_id?: string }) =>
    (await apiClient.post<{ tenant: PlatformTenant; invitation_url: string }>('/platform/tenants/', body)).data,
  setStatus: async (id: number, body: { status: string; reason?: string }) =>
    (await apiClient.post<PlatformTenantFull>(`/platform/tenants/${id}/status/`, body)).data,
  changeSubscription: async (id: number, body: Record<string, unknown>) =>
    (await apiClient.patch<PlatformTenantFull>(`/platform/tenants/${id}/subscription/`, body)).data,
  reinvite: async (id: number, email: string) =>
    (await apiClient.post<{ invitation_url: string }>(`/platform/tenants/${id}/reinvite/`, { email })).data,
  resetLink: async (id: number, email: string) =>
    (await apiClient.post<{ invitation_url: string }>(`/platform/tenants/${id}/reset-link/`, { email })).data,
  startSupport: async (id: number, reason: string) =>
    (await apiClient.post<SupportGrant>(`/platform/tenants/${id}/support/`, { reason })).data,
  endSupport: async () => (await apiClient.post<{ ended: boolean }>('/platform/support/end/')).data,
  plans: async () => (await apiClient.get<PlatformPlan[]>('/platform/plans/')).data,
  updatePlan: async (id: number, body: Record<string, unknown>) =>
    (await apiClient.patch<PlatformPlan>(`/platform/plans/${id}/`, body)).data,
  events: async (params: object) => (await apiClient.get<Paginated<PlatformEvent>>('/platform/events/', { params })).data,
}
