import apiClient from './client'
import type { AuditEntry, Invitation, Member, PaginatedResponse, PermissionDef, Role } from '@/types'

export const accessApi = {
  members: async (params?: { page?: number }) =>
    (await apiClient.get<PaginatedResponse<Member>>('/access/members/', { params })).data,
  updateMember: async (id: number, payload: { role?: number; status?: 'active' | 'suspended' }) =>
    (await apiClient.patch<Member>(`/access/members/${id}/`, payload)).data,
  removeMember: async (id: number) => { await apiClient.delete(`/access/members/${id}/`) },

  invitations: async () => (await apiClient.get<Invitation[]>('/access/invitations/')).data,
  invite: async (payload: { email: string; role: number }) =>
    (await apiClient.post<Invitation>('/access/invitations/', payload)).data,
  revokeInvitation: async (id: number) => { await apiClient.delete(`/access/invitations/${id}/`) },

  roles: async () => (await apiClient.get<Role[]>('/access/roles/')).data,
  createRole: async (payload: { name: string; permissions: string[] }) =>
    (await apiClient.post<Role>('/access/roles/', payload)).data,
  updateRole: async (id: number, payload: { name?: string; permissions?: string[] }) =>
    (await apiClient.patch<Role>(`/access/roles/${id}/`, payload)).data,
  deleteRole: async (id: number) => { await apiClient.delete(`/access/roles/${id}/`) },
  permissions: async () => (await apiClient.get<PermissionDef[]>('/access/permissions/')).data,
}

export const auditApi = {
  list: async (params?: { page?: number; action?: string; date_from?: string; date_to?: string }) =>
    (await apiClient.get<PaginatedResponse<AuditEntry>>('/audit/', { params })).data,
}

export interface InvitationPreview {
  email: string
  tenant_name: string
  role_name: string
  account_exists: boolean
}

export const invitationApi = {
  preview: async (token: string) =>
    (await apiClient.get<InvitationPreview>(`/auth/invitation/${encodeURIComponent(token)}/`)).data,
  accept: async (payload: { token: string; password: string; first_name?: string; last_name?: string }) =>
    (await apiClient.post<{ access: string; refresh: string }>('/auth/accept-invitation/', payload)).data,
}
