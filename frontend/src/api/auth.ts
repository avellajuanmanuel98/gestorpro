import apiClient, { tokenStorage } from './client'
import type { AuthTokens, Session, Tenant } from '@/types'

export interface RegisterPayload {
  email: string
  first_name: string
  last_name: string
  password: string
  password2: string
  company_name: string
}

export const authApi = {
  login: async (email: string, password: string): Promise<AuthTokens> =>
    (await apiClient.post<AuthTokens>('/auth/login/', { email, password })).data,

  /** Crea cuenta + empresa y devuelve tokens (inicio de sesión inmediato). */
  register: async (payload: RegisterPayload): Promise<AuthTokens> =>
    (await apiClient.post<AuthTokens>('/auth/register/', payload)).data,

  me: async (): Promise<Session> => (await apiClient.get<Session>('/auth/me/')).data,

  switchTenant: async (tenantId: number): Promise<AuthTokens> =>
    (await apiClient.post<AuthTokens>('/auth/switch-tenant/', {
      tenant_id: tenantId, refresh: tokenStorage.refresh,
    })).data,

  /** Revoca el refresh token en el servidor. */
  logout: async (): Promise<void> => {
    const refresh = tokenStorage.refresh
    if (refresh) await apiClient.post('/auth/logout/', { refresh })
  },
}

export const tenantApi = {
  current: async (): Promise<Tenant> => (await apiClient.get<Tenant>('/tenant/')).data,
  update: async (payload: Partial<Tenant>): Promise<Tenant> =>
    (await apiClient.patch<Tenant>('/tenant/', payload)).data,
}
