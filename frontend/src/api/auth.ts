import apiClient from './client'
import type { AuthTokens, PlanSummary, Session, Tenant } from '@/types'

export interface RegisterPayload {
  email: string
  first_name: string
  last_name: string
  password: string
  password2: string
  company_name: string
  vertical?: string
}

/** Personal de la plataforma: tras la contraseña falta el código de su app autenticadora. */
export interface MfaChallenge {
  mfa: 'verify'
  mfa_token: string
}

export const isMfaChallenge = (r: AuthTokens | MfaChallenge): r is MfaChallenge => 'mfa' in r

export const authApi = {
  login: async (email: string, password: string): Promise<AuthTokens | MfaChallenge> =>
    (await apiClient.post<AuthTokens | MfaChallenge>('/auth/login/', { email, password })).data,

  verifyMfa: async (mfaToken: string, code: string): Promise<AuthTokens> =>
    (await apiClient.post<AuthTokens>('/auth/mfa/verify/', { mfa_token: mfaToken, code })).data,

  /** Crea cuenta + empresa y devuelve tokens (inicio de sesión inmediato). */
  register: async (payload: RegisterPayload): Promise<AuthTokens> =>
    (await apiClient.post<AuthTokens>('/auth/register/', payload)).data,

  me: async (): Promise<Session> => (await apiClient.get<Session>('/auth/me/')).data,

  switchTenant: async (tenantId: number): Promise<AuthTokens> =>
    (await apiClient.post<AuthTokens>('/auth/switch-tenant/', { tenant_id: tenantId })).data,

  /** Cierra la sesión de soporte de la plataforma (el token de soporte deja de servir). */
  endSupport: async (): Promise<void> => { await apiClient.post('/platform/support/end/') },

  /** "¿Olvidaste tu contraseña?": nunca revela si la cuenta existe. */
  forgotPassword: async (email: string): Promise<{ email_enabled: boolean }> =>
    (await apiClient.post('/auth/password/forgot/', { email })).data,
  checkReset: async (uid: string, token: string): Promise<{ valid: boolean; email: string | null }> =>
    (await apiClient.get(`/auth/password/reset/${uid}/${token}/`)).data,
  resetPassword: async (uid: string, token: string, password: string, password2: string): Promise<void> => {
    await apiClient.post(`/auth/password/reset/${uid}/${token}/`, { password, password2 })
  },

  /** Revoca el refresh token (cookie httpOnly) en el servidor y la borra. */
  logout: async (): Promise<void> => { await apiClient.post('/auth/logout/') },
}

export const tenantApi = {
  current: async (): Promise<Tenant> => (await apiClient.get<Tenant>('/tenant/')).data,
  update: async (payload: Partial<Tenant>): Promise<Tenant> =>
    (await apiClient.patch<Tenant>('/tenant/', payload)).data,
  plan: async (): Promise<PlanSummary> => (await apiClient.get<PlanSummary>('/tenant/plan/')).data,
}
